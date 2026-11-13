# System Monitor 後端架構

後端以責任與依賴方向分層，平台 API 與獨立採集器共用應用服務。程式碼位於 `projects/system-monitor/backend/src/`；`src` 本身是 Python 套件，專案自己的 `main.py` 已移除。

## 目錄與職責

```text
src/
├── plugin.py
├── bootstrap.py
├── api/
│   ├── router.py
│   ├── dependencies.py
│   ├── exception_handlers.py
│   ├── routes/{overview,history,health}.py
│   └── schemas/{overview,history,health}.py
├── services/
│   ├── overview.py
│   ├── history.py
│   ├── health.py
│   ├── collection.py
│   ├── ports.py
│   └── exceptions.py
├── domain/
│   ├── metrics.py
│   ├── history.py
│   ├── health.py
│   ├── health_rules.py
│   ├── aggregation.py
│   └── serialization.py
├── infrastructure/
│   ├── metrics/{cpu,memory,network,disk_io,gpu,source}.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── migration_runner.py
│   │   └── migrations/{001_initial,002_gpu_disk_io}.sql
│   ├── repositories/metrics_repository.py
│   ├── storage/collector_status.py
│   └── process_lock.py
├── collector/
│   ├── metrics_collector.py
│   └── runner.py
└── core/
    ├── config.py
    └── logging.py
```

| 層 | 責任 | 依賴限制 |
|---|---|---|
| API | HTTP 參數、回應驗證、依賴注入、例外轉換 | 路由不直接使用硬體或資料庫 |
| Services | 組合總覽、查詢區間、健康報告與採集流程 | 依賴 ports 與 domain，不匯入基礎設施實作 |
| Domain | 不可變快照、歷史樣本、狀態、健康規則與降採樣 | 不依賴 FastAPI、Pydantic、psutil、SQLite |
| Infrastructure | psutil、GPU 指令、SQLite、JSON 與程序鎖 | 實作服務需要的外部能力 |
| Bootstrap | 建立實作物件並注入服務 | 唯一集中組裝具體實作的位置 |
| Collector | CLI、訊號、程序鎖與定時執行 | 採集與清理交給 CollectionService |
| Core | 設定解析與日誌配置 | 不啟動排程或建立資料庫 |

## 入口與服務生命週期

平台仍由 `backend/app/main.py` 啟動，根據 manifest 載入 `src/plugin.py`。每次 `build_router()` 回傳新的父 router，正式與相容 API 前綴仍共用同一個 Runtime。API 的 `dependencies.py` 取得服務，測試使用 FastAPI `dependency_overrides` 替換服務。

`bootstrap.get_runtime()` 以已解析的 Settings 作為快取鍵。組裝入口以鎖保護同時首次載入，確保同一設定只建立一組採集器、Repository 與服務；不同資料庫設定使用不同 Runtime。沒有長時間開啟的資料庫連線，建立 Runtime 不讀硬體、不建表、不啟動背景程序。Runtime 快取最多保留 16 組設定；正常部署只使用一組設定，測試應使用依賴覆寫或明確建構服務。

CPU 預熱、網路累計基準、磁碟讀寫基準、GPU 快取與相關鎖皆由實例持有。總覽、健康檢查與同程序中的採集服務共用來源，避免每次 HTTP 請求重設取樣狀態。背景採集器是另一個程序，因此有自己的 Runtime。

## SQL、連線與遷移

- `connection.py` 管理短生命週期連線、WAL、busy timeout、鎖定重試及唯讀模式。
- `migration_runner.py` 在 `BEGIN IMMEDIATE` 之後重新讀取版本，於同一交易逐條執行 SQL。沒有使用會隱式提交的 `executescript()`。
- `001_initial.sql` 建立原始六欄指標；`002_gpu_disk_io.sql` 新增三個 nullable 欄位。schema 維持 v2，既有樣本不補零。
- `metrics_repository.py` 集中樣本的 INSERT、SELECT、DELETE，Repository 方法負責開啟與關閉操作所需的連線。
- 保留目前寫入／一般歷史查詢自動初始化與遷移的時機。健康探測透過唯讀模式查詢，不建檔、不遷移。
- 過期時間由 CollectionService 決定，Repository 只刪除嚴格早於截止時間的樣本。

預設仍使用平台 `backend/data/metrics.db`，環境變數 `A7LAS_METRICS_DB_PATH` 可覆寫。不需刪除或重建現有資料庫。

## API 與資料模型

公開 API 維持 `/overview`、`/history`、`/feature-health`，平台同時掛載於 `/api/system-monitor` 與相容的 `/api` 前綴。HTTP 欄位、Pydantic 驗證與歷史錯誤的 503 訊息保持不變。

內部資料使用 domain dataclass；API Schema 使用 Pydantic。轉換在 HTTP 邊界完成，資料庫不依賴回應模型。歷史降採樣維持 15m／1h 原始樣本、24h 五分鐘桶、7d 三十分鐘桶。

健康規則只判斷傳入證據，HealthService 負責取得證據、捕捉單項例外、保存最近成功時間與三秒報告快取。狀態、Latest Result、原始資料與錯誤堆疊來自同次檢查。有效零值仍正常；GPU 無支援來源為 Unavailable；首次速率取樣為 Unknown；歷史寫入超過 90 秒為 Issues。診斷來源文字隨模組位置更新。

## 採集器與設定

原指令保留，從儲存庫根目錄執行：

```bash
PYTHONPATH=projects/system-monitor/backend backend/.venv/bin/python -m src.collector.metrics_collector
```

CLI 只設定日誌、停止訊號、取得程序鎖並呼叫 runner。runner 每 30 秒執行 CollectionService，啟動時與每小時進行維護，保留七天樣本。診斷旁檔仍以原子方式取代，寫入診斷失敗會記錄日誌並讓採集流程繼續。

`core/config.py` 集中現有政策與預設值，這次沒有新增對外環境變數。`core/logging.py` 僅由採集器 CLI 設定 root logging，平台掛載時沿用平台設定。專案需求維持 `requirements.txt`；平台的 `backend/constraints.txt` 約束已驗證的共用環境版本，新增依賴後需重新解析並測試。

## 驗證與維護

- `tests/unit/`：純規則、降採樣、應用服務替身與架構依賴限制。
- `tests/integration/`：SQLite、v1→v2 遷移與回滾、唯讀、旁檔、硬體介面與背景程序。
- `tests/api/`：新舊前綴、參數、回應格式、錯誤訊息與依賴覆寫。
- `monitor_backend.py` 取得平台實際隔離載入的模組，測試不建立第二份採集狀態。
- `monitor_support.py` 僅負責舊行為測試所需的建構工具，實際操作仍經過新的服務與 Repository。

```bash
backend/.venv/bin/python -m pytest backend/tests projects/system-monitor/backend/tests -q
```

架構測試會阻止 domain／services 匯入 HTTP 或基礎設施，也檢查 SQL 執行限於 database／repositories。Ubuntu GPU 的真實硬體仍需在部署主機驗證；本機測試涵蓋模擬驅動回應與 macOS 不支援的情況。

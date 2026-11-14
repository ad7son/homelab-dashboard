# 共用事件與專案健康度

## 用途與邊界

平台統一保存各專案的結構化 log，依功能的實際執行結果提供 Project
Health。專案負責宣告功能與回報證據；System Monitor 負責顯示。
新增專案不需修改健康 API 或前端清單。

## 架構

```text
backend/app/observability/
├── config.py       # 儲存位置與保留政策
├── models.py       # 事件、功能宣告與健康回應契約
├── events.py       # 回報入口、Python logging 整合與清理生命週期
├── storage.py      # SQLite 交易與事件查詢
├── schema.sql     # 歷史事件與最新功能狀態
├── health.py      # 依事件證據判定健康狀態
└── router.py      # 平台健康與事件查詢 API
```

平台載入 plugin 的功能宣告，先初始化事件系統，再啟動各專案生命週期；
關閉時順序相反，讓停止期間的事件仍可保存。API 與採集子程序共用相同
資料庫與事件格式。

| 所在位置 | 責任 |
|---|---|
| 平台 `observability/` | 格式、保存、保留政策、判定及查詢 |
| 專案 `plugin.py` | 宣告功能名稱、類型與定期回報期限 |
| 專案執行程式 | 回報成功、失敗、不可用及原始例外 |
| System Monitor 前端 | 顯示所有啟用專案、判定依據與事件證據 |

## 事件與健康判定

事件以版本化 JSON 保存，包含時間、專案、功能、級別、執行結果、耗時、
來源、例外與補充證據。完整欄位以 `models.py` 為準。

`level` 表示 log 嚴重程度，`outcome` 表示功能執行結果。一般 Python
logging 會轉成共用格式，但只有具備功能 ID 與明確 outcome 的事件才更新
健康狀態；不解析訊息文字，也不把每筆 ERROR 當成整個專案故障。

| 功能類型 | 判定方式 |
|---|---|
| `scheduled` | 最近結果加上成功回報期限；持續沒有成功回報即為 issues |
| `request` | 最近一次實際執行結果；無請求時不因時間經過而判定故障 |

成功為 healthy，失敗為 issues，明確不支援為 unavailable。尚無結果為
unknown；定期功能超過首次等待期限則轉為 issues。未知結果不延長成功
期限。不支援的功能不套用定期逾時判定。

健康查詢只讀取已保存的證據，不另行操作硬體或發送測試請求。健康狀態
表示已觀測到的執行結果，不能保證下一次執行成功。

## 專案接入

在 plugin 宣告穩定的功能識別碼：

```python
from app.observability import models


def get_health_features() -> tuple[models.FeatureDefinition, ...]:
    return (
        models.FeatureDefinition(
            id="sync",
            name="資料同步",
            mode="scheduled",
            stale_after_seconds=30,
        ),
    )
```

在實際工作處回報。`execution` 自動保存耗時與成功／失敗，並將原始例外
繼續向外傳遞；需表達不可用或未知時使用 `events.record()`。

```python
from app.observability import events

with events.execution("my-project", "sync", source=__name__):
    synchronize()
```

專案 ID 必須對應 manifest，功能 ID 必須對應 plugin 宣告。一般 log 可
沿用 `logging.getLogger(__name__)`；補充證據不要包含憑證或請求機密。
獨立子程序須能匯入平台 `backend/app`，並使用相同的事件資料庫路徑；
System Monitor 的程序管理器會傳入所需 Python 路徑。

## 儲存與保留

預設位置為儲存庫根目錄 `data/platform/observability.db`，可用
`A7LAS_OBSERVABILITY_DB_PATH` 覆寫。與各專案的業務資料分開，SQLite
WAL 支援 API 與子程序並行存取。

`events` 保存歷史紀錄；`feature_state` 保存最新執行結果與最近成功時間。
兩者同交易更新，較晚到達的舊事件不覆蓋較新的結果。狀態跨重啟保留，
舊事件清理後仍可判定功能是否停止回報。

`config.py` 的 `EVENT_RETENTION_DAYS` 預設七天，`None` 表示全部保留。
每天清理一次，不在啟動時清理；重啟會重新計算清理間隔。只清歷史事件，
最新功能狀態持續保存。刪除後空間供後續寫入重用，不自動縮檔。

事件寫入失敗會輸出警告，不使原本的業務操作失敗；健康畫面可能暫時
停留在舊結果，定期功能仍會依期限變為 issues。

## 平台 API

| 路徑 | 用途 |
|---|---|
| `GET /api/project-health` | 所有啟用專案的健康報告 |
| `GET /api/project-health/{project_id}` | 單一專案、判定依據及最近事件證據 |
| `GET /api/logs` | 依 project_id、feature_id、level 篩選事件 |

事件依 ID 倒序排列，透過 `limit` 與 `before_id` 分頁，每頁最多 100 筆。
健康查詢不寫入自己的執行事件，避免查詢本身產生監測迴圈。
事件儲存不可用時回傳 503，不用空清單或假成功掩蓋故障。

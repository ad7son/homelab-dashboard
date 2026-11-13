"""System Monitor 後端套件，供平台掛載 API 與獨立採集器共用。

平台以動態命名空間隔離專案，套件內保留相對模組路徑，避免匯入另一份 src。
匯入套件不啟動採集器，也不建立資料庫。"""

from __future__ import annotations

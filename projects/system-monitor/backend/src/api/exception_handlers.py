"""將應用層錯誤轉為既有 HTTP 契約；底層訊息只保留於日誌。"""

from __future__ import annotations

import logging

import fastapi

_logger = logging.getLogger("a7las.history")


def history_unavailable(error: Exception) -> fastapi.HTTPException:
    """記錄原始堆疊，建立不暴露底層錯誤內容的 503 例外。

    Args:
        error: 應用服務傳來、包含原始 cause 的例外。

    Returns:
        保留既有公開 detail 的 HTTPException，由路由引發。
    """
    _logger.error(
        "Failed to query historical metrics database",
        exc_info=(type(error), error, error.__traceback__),
    )
    return fastapi.HTTPException(
        status_code=503, detail="Historical metrics database unavailable"
    )

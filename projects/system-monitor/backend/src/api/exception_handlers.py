"""將應用層錯誤轉為既有 HTTP 契約；底層訊息只保留於日誌。"""
import logging
from fastapi import HTTPException

logger = logging.getLogger("a7las.history")


def history_unavailable(error: Exception) -> HTTPException:
    logger.error("Failed to query historical metrics database", exc_info=(type(error), error, error.__traceback__))
    return HTTPException(status_code=503, detail="Historical metrics database unavailable")

"""將不可變快照轉成容器資料，供診斷證據與 API 邊界使用。"""

from __future__ import annotations

import dataclasses
import enum
from typing import Any


def to_dict(value: Any) -> Any:
    """遞迴轉換 dataclass、Enum 與容器，不修改原始快照。

    Args:
        value: 待轉換值；不認識的葉節點原樣回傳。

    Returns:
        dataclass 轉為字典、Enum 轉為值，tuple／list 轉為清單的結果。
        非有限浮點數仍保留原值，另由健康規則的 json_safe 處理。
    """
    if dataclasses.is_dataclass(value):
        return to_dict(dataclasses.asdict(value))
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    return value

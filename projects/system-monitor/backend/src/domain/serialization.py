"""將不可變快照轉成 JSON 可表達的資料，供診斷證據與 API 邊界使用。"""
from dataclasses import asdict, is_dataclass
from enum import Enum


def to_dict(value):
    if is_dataclass(value):
        return to_dict(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    return value

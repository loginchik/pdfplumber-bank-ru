from dataclasses import dataclass, fields
from typing import Dict, Union


@dataclass(frozen=True, eq=True)
class CellBoundary:
    left: float
    right: float


@dataclass(frozen=True)
class Word:
    text: str
    x0: float
    x1: float
    top: float

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, float]]) -> "Word":
        return cls(**{field.name: data.get(field.name) for field in fields(cls)})

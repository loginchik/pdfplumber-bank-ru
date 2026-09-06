from dataclasses import dataclass, fields
from typing import Dict, Union


@dataclass(frozen=True, eq=True)
class CellBoundary:
    """
    Структура для границ ячейки в таблице
    """

    left: float
    right: float


@dataclass(frozen=True)
class Word:
    """
    Структура слова, извлекаемого из PDF-страницы
    """

    text: str
    x0: float
    x1: float
    top: float

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, float]]) -> "Word":
        """
        Преобразует словарь ``pdfplumber`` в структуру текущего класса

        :param data: словарь ``pdfplumber``
        :return: объект ``Word``
        """
        return cls(**{field.name: data.get(field.name) for field in fields(cls)})

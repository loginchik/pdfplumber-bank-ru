from logging import getLogger
from pathlib import Path
from typing import List

from pdfplumber.page import Page

from .enums import BankNameEnum
from .schemas import Word


class BasicProcessor:
    """
    Базовый обработчик

    Задает общие для разных структур статичные методы и параметры класса
    """

    BANK_NAME: BankNameEnum = None

    def __init__(self, **kwargs) -> None:
        self.logger = getLogger(self.__class__.__name__)

    @staticmethod
    def get_words(page: Page, x_tolerance: int = 3, y_tolerance: int = 3) -> List[Word]:
        """
        Извлекает все слова с текущей страницы с заданной толерантностью в пикселях

        :param page: страница pdfplumber
        :param x_tolerance: горизонтальная толерантность
        :param y_tolerance: вертикальная толерантность
        :return: слова со страницы
        """
        return [Word.from_dict(w) for w in page.extract_words(x_tolerance=x_tolerance, y_tolerance=y_tolerance)]

    @staticmethod
    def validate_pdf_file(filepath: Path) -> None:
        """
        Валидирует путь к файлу, чтобы он поддерживался текущим процессом

        :param filepath: путь к файлу
        :raise FileNotFoundError: файл не найден или не является файлом
        :raise ValueError: некорректное расширение
        """
        if not filepath.exists() or not filepath.is_file():
            raise FileExistsError(f"file not found: {filepath}")
        if not filepath.suffix == ".pdf":
            raise ValueError(f"file extension not supported: {filepath.suffix}. expected .pdf")

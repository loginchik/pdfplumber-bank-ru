from logging import getLogger
from typing import List

from pdfplumber.page import Page

from .enums import BankNameEnum
from .schemas import Word


class BasicProcessor:
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

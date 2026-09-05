from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List, Optional, Any

import pandas as pd
import pdfplumber
from pdfplumber.pdf import PDF
from pdfplumber.page import Page

from commons.base import BasicProcessor
from commons.enums import BankNameEnum, TableColumnEnum
from commons.schemas import Word, CellBoundary


class BaseTablePageExtractor(ABC, BasicProcessor):
    """
    Обработчик одной страницы банковской выписки

    Определяет методы для извлечения структуры таблицы со страницы
    и воссоздания этой таблицы в формате `pandas.DataFrame`
    """

    BANK_NAME: BankNameEnum = None

    def __init__(self, page: Page) -> None:
        super().__init__(page=page)
        self.words: List[Word] = self.get_words(page)
        self.__boundaries: Optional[List[CellBoundary]] = None
        self.__table_located: bool = False

    def convert_to_frame(self, boundaries: Optional[List[CellBoundary]] = None) -> pd.DataFrame:
        """
        Преобразует содержимое страницы в таблицу в формате `pandas.DataFrame`

        Если структура не задана, определяет её на основе содержимого текущей страницы.
        Если внешняя структура таблицы задана, то применяет её без промежуточной валидации

        :param boundaries: внешняя структура таблицы
        :return: образованный фрейм
        """
        try:
            self.locate_table()
        except ValueError as e:
            self.logger.error("failed to find first cell", exc_info=e)
            return pd.DataFrame(columns=list(self.pdf_columns))

        if boundaries is None:
            try:
                boundaries = self._get_cell_boundaries()
            except ValueError as e:
                self.logger.error("failed to determine columns boundaries", exc_info=e)
                return pd.DataFrame(columns=list(self.pdf_columns))

        return self.words_to_frame(bounds=boundaries)

    def get_cell_boundaries(self) -> List[CellBoundary]:
        if self.__boundaries is None:
            if not self.__table_located:
                self.locate_table()
            self.__boundaries = self._get_cell_boundaries()
        return self.__boundaries

    def locate_table(self) -> Word:
        word, i = self._locate_table()
        self.words = self.words[i:]
        self.__table_located = True
        return word

    @property
    @abstractmethod
    def pdf_columns(self) -> Tuple[str, ...]: ...

    @property
    def pdf_columns_word_count(self) -> int:
        """
        Суммарное количество слов в строке-заголовке таблицы
        """
        return sum(len(w.split()) for w in self.pdf_columns)

    @property
    def pdf_columns_count(self) -> int:
        return len(self.pdf_columns)

    @abstractmethod
    def _locate_table(self) -> Tuple[Word, int]: ...

    @abstractmethod
    def _get_cell_boundaries(self) -> List[CellBoundary]: ...

    @abstractmethod
    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame: ...

    @staticmethod
    def _get_first_cell(words: List[Word], target_words: List[str]) -> Tuple[Word, int]:
        """
        Находит координаты и содержимое первого слова первой ячейки таблицы

        Последовательно проверяет сочетания слов и находит начало строки,
        которая совпадает с целевым набором слов

        :param words: слова со страницы
        :param target_words: целевые слова - часть названия первой колонки
        :return: первое слово в ячейке, индекс слова в исходном массиве
        """
        target_collocation = " ".join(target_words)

        for i, word in enumerate(words):
            current_collocation = " ".join([w.text for w in words[i : i + len(target_words)]])
            if current_collocation == target_collocation:
                return word, i
        raise ValueError()

    @staticmethod
    def bound_to_cell(word: pd.Series, bounds: List[CellBoundary]) -> Optional[int]:
        """
        Находит предел, в рамках которого лежит текущее слово

        :param word: слово с границами
        :param bounds: границы ячеек
        :return: номер ячейки
        """
        return next((i for i, bound in enumerate(bounds) if word["x0"] >= bound.left and word["x1"] <= bound.right), None)


class BaseTableExtractor(ABC, BasicProcessor):
    """
    Обработчик PDF-документа выписки из банка: извлекает таблицы с транзакциями
    с каждой страницы отдельным обработчиком `PAGE_CLASS` и образует из них один общий фрейм
    """

    BANK_NAME: BankNameEnum = None

    page_processor_class: BaseTablePageExtractor = None
    table_columns: Tuple[TableColumnEnum] = None

    def extract_from_file(self, filepath: Path) -> pd.DataFrame:
        """
        Открывает заданный PDF-файл и извлекает из него все транзакции

        :param filepath: путь к файлу
        :return: образованный фрейм
        :raise ValueError: ни одна таблица не образована
        """
        with pdfplumber.open(filepath) as pdf:
            return self.extract_from_pdf(pdf)

    def extract_from_pdf(self, pdf: PDF) -> pd.DataFrame:
        """
        Извлекает все таблицы из открытого PDF-файла и образует общий фрейм

        :param pdf: открытый PDF-файл
        :return: фрейм со всеми транзакциями из файла
        :raise ValueError: ни одна таблица не образована
        """
        boundaries = None

        dfs = []
        for p, page in enumerate(pdf.pages, start=1):
            page_processor = self._get_page_processor(page)
            if p == 1 and boundaries is None:
                boundaries = page_processor.get_cell_boundaries()

            df = page_processor.convert_to_frame(boundaries=boundaries)
            if df.shape[0] > 0:
                df.columns = list(self.table_columns)
                df[TableColumnEnum.page_no] = p
                df[TableColumnEnum.bank_name] = self.BANK_NAME
                dfs.append(df)

        if len(dfs) == 0:
            raise ValueError("no table extracted from pdf")

        dfs = self._update_merged_pages(df=pd.concat(dfs, axis=0, ignore_index=True))
        dfs.columns = [col.value if not isinstance(col, str) else col for col in dfs.columns]
        return dfs

    def _get_page_processor(self, page: Page) -> Any:
        """
        Создаёт обработчик для страницы из PDF-выписки

        :param page: страница выписки
        :return: обработчик для этой страницы
        :raise ValueError: целевой класс обработчика не задан
        """
        if self.page_processor_class is None:
            raise ValueError("page processor class is not specified")
        return self.page_processor_class(page=page)

    @abstractmethod
    def _update_merged_pages(self, df: pd.DataFrame) -> pd.DataFrame: ...

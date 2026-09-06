from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List, Optional, Any, Dict

import numpy as np
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
                boundaries = self.get_cell_boundaries()
            except ValueError as e:
                self.logger.error("failed to determine columns boundaries", exc_info=e)
                return pd.DataFrame(columns=list(self.pdf_columns))

        return self.words_to_frame(bounds=boundaries).reset_index(drop=True)

    def get_cell_boundaries(self) -> List[CellBoundary]:
        """
        Возвращает или уже определённые, или впервые определённые границы
        ячеек в таблице на текущей странице

        :return: границы ячеек в таблице на странице
        """
        if self.__boundaries is None:
            if not self.__table_located:
                self.locate_table()

            bounds_df = self._get_cell_boundaries()
            self._validate_bounds_df(bounds_df)

            bounds_df["right"] = bounds_df["left"].shift(-1).fillna(np.inf)
            self.__boundaries = [
                CellBoundary(**bound) for bound in bounds_df.sort_values("cell")[["left", "right"]].to_dict(orient="records")
            ]

        return self.__boundaries

    def locate_table(self) -> Word:
        """
        Определяет начало таблицы и обрезает внутренний список слов так,
        чтобы он начинался сразу с таблицы

        :return: первое слово в таблице
        """
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
        """
        Количество колонок в таблице в PDF-файле
        """
        return len(self.pdf_columns)

    @abstractmethod
    def _locate_table(self) -> Tuple[Word, int]: ...

    @abstractmethod
    def _get_cell_boundaries(self) -> pd.DataFrame: ...

    @abstractmethod
    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame: ...

    def _group_df_to_records(self, df: pd.DataFrame, rename_columns: bool = True, drop_index: bool = True) -> pd.DataFrame:
        """
        Группирует сырой фрейм по строкам и столбцам, чтобы образовать таблицу с транзакциями

        :param df: исходный фрейм
        :param rename_columns: устанавливать ли названия колонок
        :param drop_index:
        :return: записи о транзакциях
        """
        df = df.groupby(["row", "cell"])["text"].agg(lambda x: " ".join(x)).unstack("cell")
        if rename_columns:
            df.columns = list(self.pdf_columns)

        df = df.reset_index(drop=drop_index)
        return df

    def _validate_bounds_df(self, bounds_df: pd.DataFrame) -> None:
        """
        Сопоставляет количество колонок, для которых определены границы,
        с ожидаемым количеством колонок

        :param bounds_df: фрейм с границами колонок таблицы
        :raise ValueError:
        """
        if (determined_columns_count := bounds_df["left"].shape[0]) != self.pdf_columns_count:
            raise ValueError(
                "number of columns does not match expected: {} != {}".format(determined_columns_count, self.pdf_columns_count)
            )

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
        self.validate_pdf_file(filepath)
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

    @staticmethod
    def _update_money_amount_columns(df: pd.DataFrame, additional_replacements: Optional[Dict[str, str]]) -> pd.DataFrame:
        """
        Извлекает валюту из колонки с суммой операции в валюте операции
        и преобразует колонки с суммами операций в числовые значения

        :param df: фрейм
        :param additional_replacements: дополнительные замены
        :return: обновлённый фрейм
        """
        if TableColumnEnum.money_op_curr in df.columns:
            df[TableColumnEnum.currency] = df[TableColumnEnum.money_op_curr].str[-1]

        money_columns = list({TableColumnEnum.money_op_curr, TableColumnEnum.money_acc_curr} & set(df.columns))
        for col in money_columns:
            if additional_replacements is not None:
                for repl_before, repl_after in additional_replacements.items():
                    df[col] = df[col].str.replace(repl_before, repl_after)

            df[col] = pd.to_numeric(df[col].str.replace(r"[^-+,0-9]", "", regex=True).str.replace(",", "."), errors="coerce")

        return df

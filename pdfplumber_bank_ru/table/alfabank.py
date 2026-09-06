from typing import List, Tuple

import pandas as pd

from pdfplumber_bank_ru.commons.schemas import Word, CellBoundary
from pdfplumber_bank_ru.commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class AlfaBankTablePageExtractor(BaseTablePageExtractor):
    """
    Обработчик одной страницы банковской выписки Альфа-Банка

    Извлекает содержимое страницы и преобразует в ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.ALFA

    @property
    def pdf_columns(self) -> Tuple[str, ...]:
        return "Дата проводки", "Код операции", "Описание", "Сумма в валюте счета"

    def _locate_table(self) -> Tuple[Word, int]:
        """
        Определяет начало таблицы по полному названию первой колонки

        :return: координаты первой ячейки таблицы
        """
        return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split())

    def _get_cell_boundaries(self) -> pd.DataFrame:
        """
        Определяет границы ячеек искомой таблицы

        :return: границы ячеек в таблице слева направо
        :raise ValueError:
        """

        def _get_text_cell(v: str) -> int:
            return next(i for i, cell in enumerate(self.pdf_columns) if v in cell.split())

        df = pd.DataFrame(self.words[: self.pdf_columns_word_count])
        df["cell"] = df["text"].apply(_get_text_cell)

        bounds_df = df.groupby("cell")["x0"].min().rename("left").reset_index(drop=False)
        return bounds_df

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        """
        Преобразует содержимое страницы в таблицу с данными транзакций

        :param bounds: границы ячеек
        :return: фрейм с транзакциями с этой страницы
        """
        df = pd.DataFrame(self.words[self.pdf_columns_word_count :])
        df["cell"] = df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        df["row"] = (df["cell"] < df["cell"].shift(1)).cumsum()

        df = self._group_df_to_records(df)
        df = df[df[self.pdf_columns[0]].isna() | df[self.pdf_columns[0]].str.match(r"\d{2}\.\d{2}\.\d{4}")]
        df["row"] = df[self.pdf_columns[0]].notna().cumsum()
        df = df.groupby("row").agg(lambda x: " ".join(x.dropna())).reset_index(drop=True)

        return df.reset_index(drop=True)


class AlfaBankTableExtractor(BaseTableExtractor):
    """
    Обработчик PDF-выписки из Альфа-Банка

    Извлекает с каждой страницы содержимое таблицы с транзакциями и образует ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.ALFA
    page_processor_class = AlfaBankTablePageExtractor
    table_columns = (
        TableColumnEnum.date,
        TableColumnEnum.document_number,
        TableColumnEnum.details,
        TableColumnEnum.money_acc_curr,
    )

    def _update_merged_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Преобразует типы данных в объединённом фрейме и очищает невалидные значения

        :param df: исходный общий фрейм
        :return: итоговый общий фрейм
        """
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date], format="%d.%m.%Y", errors="coerce")
        df = df.dropna(subset=[TableColumnEnum.date])

        df = self._update_money_amount_columns(df, additional_replacements=None)
        df[TableColumnEnum.card_number] = df[TableColumnEnum.details].str.extract(r"(2\d+\++\d+)")[0]

        return df

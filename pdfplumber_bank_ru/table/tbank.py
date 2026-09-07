from typing import List, Tuple

import pandas as pd
import numpy as np

from pdfplumber_bank_ru.commons.schemas import Word, CellBoundary
from pdfplumber_bank_ru.commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class TBankTablePageExtractor(BaseTablePageExtractor):
    """
    Обработчик одной страницы банковской выписки ТБанка

    Извлекает содержимое страницы и преобразует в ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.TBANK

    @property
    def pdf_columns(self) -> Tuple[str, ...]:
        return (
            "Дата и время операции",
            "Дата списания",
            "Сумма в валюте операции",
            "Сумма операции в валюте договора",
            "Описание операции",
            "Номер карты",
        )

    def _locate_table(self) -> Tuple[Word, int]:
        """
        Определяет начало таблицы по полному названию первой колонки

        :return: координаты первой ячейки таблицы
        """
        return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split()[:-1])

    def _get_cell_boundaries(self) -> pd.DataFrame:
        """
        Определяет границы ячеек искомой таблицы

        :return: границы ячеек в таблице слева направо
        :raise ValueError:
        """
        df = pd.DataFrame(self.words[: self.pdf_columns_word_count])
        df["cell"] = ((df["x0"].astype(int) == df["x0"]).cumsum() - 1) % self.pdf_columns_count

        bounds_df = df.groupby("cell", sort=False)["x0"].min().rename("left").reset_index(drop=False)
        return bounds_df

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        """
        Преобразует содержимое страницы в таблицу с данными транзакций

        :param bounds: границы ячеек
        :return: фрейм с транзакциями с этой страницы
        """
        df = pd.DataFrame(self.words[self.pdf_columns_word_count :])

        df["cell"] = df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        df = df.dropna(subset="cell").reset_index(drop=True)
        df["cell"] = df["cell"].astype(int)
        df["row"] = (df["cell"] == 0).cumsum() - 1
        df = df[df["row"] >= 0]
        if df.shape[0] == 0:
            return pd.DataFrame(columns=self.pdf_columns)

        df = self._group_df_to_records(df, drop_index=False)
        df = df[df[self.pdf_columns[0]].str.match(r"^\d{2}.\d{2}(.\d{4})?$")]
        df["row"] = np.where(df[self.pdf_columns[0]].str.match(r"^\d{2}\:\d{2}"), np.nan, df["row"])
        df["row"] = df["row"].ffill()
        df = df.groupby("row").agg(lambda x: " ".join(x.dropna())).reset_index(drop=True)

        return df


class TBankTableExtractor(BaseTableExtractor):
    """
    Обработчик PDF-выписки из ТБанка

    Извлекает с каждой страницы содержимое таблицы с транзакциями и образует ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.TBANK
    page_processor_class = TBankTablePageExtractor
    table_columns = (
        TableColumnEnum.date,
        TableColumnEnum.date_performed,
        TableColumnEnum.money_op_curr,
        TableColumnEnum.money_acc_curr,
        TableColumnEnum.details,
        TableColumnEnum.card_number,
    )

    def _update_merged_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Преобразует типы данных в объединённом фрейме, очищает невалидные значения
        и насыщает таблицу дополнительными данными из деталей транзакции

        :param df: исходный общий фрейм
        :return: итоговый общий фрейм
        """
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date], format="%d.%m.%Y %H:%M")
        df[TableColumnEnum.date_performed] = pd.to_datetime(df[TableColumnEnum.date_performed], format="%d.%m.%Y %H:%M")
        df = df.dropna(subset=[TableColumnEnum.date])

        df = self._update_money_amount_columns(df, additional_replacements=None)
        df[TableColumnEnum.card_number] = (
            df[TableColumnEnum.card_number].str.replace(r"[^0-9]", "", regex=True).str.strip().mask(lambda x: x == "", np.nan)
        )
        df[TableColumnEnum.to_account] = df[TableColumnEnum.details].str.extract(r"на договор (\d+)")
        df[TableColumnEnum.from_account] = df[TableColumnEnum.details].str.extract(r"с договора (\d+)")

        return df

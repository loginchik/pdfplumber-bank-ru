import re
from typing import List, Tuple

import pandas as pd
import numpy as np

from commons.schemas import Word, CellBoundary
from commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class OzonBankTablePageExtractor(BaseTablePageExtractor):
    """
    Обработчик одной страницы банковской выписки Ozon Банка

    Извлекает содержимое страницы и преобразует в ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.OZON

    @property
    def pdf_columns(self) -> Tuple[str, ...]:
        return (
            "Дата операции",
            "Документ",
            "Назначение платежа",
            "Сумма операции в российских рублях",
            "Сумма операции в валюте",
        )

    def _locate_table(self) -> Tuple[Word, int]:
        """
        Определяет начало таблицы по части названия первой колонки

        Метод применим только к первой странице банковской выписки,
        так как последующие страницы не содержат названия колонок.
        Для остальных страниц выписки предполагает, что первое слово
        на странице, если является датой, - первая ячейка таблицы

        :return: координаты первой ячейки таблицы
        """
        try:
            return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split()[:2])
        except ValueError:
            if re.match(r"^(\d{2}\.){2}\d{4}$", (word := self.words[0]).text) and re.match(
                r"^(\d{2}:){2}\d{2}$", self.words[1].text
            ):
                return word, 0
            raise

    def _get_cell_boundaries(self) -> pd.DataFrame:
        """
        Определяет границы ячеек искомой таблицы

        Метод применим только к первой странице выписки: последующие страницы
        не содержат названия колонок

        :return: границы ячеек в таблице слева направо
        :raise ValueError:
        """
        if re.match(r"^(\d{2}\.){2}\d{4}$", self.words[0].text):
            raise ValueError("boundaries must be collected on the first page")

        df = pd.DataFrame(self.words)
        df = df[(df["x0"] == df["x0"].min()).cumsum() == 1]
        df = df[df["text"].str.capitalize() == df["text"]]
        df["cell"] = np.arange(df.shape[0])

        bounds_df = df.groupby("cell", sort=False)["x0"].min().rename("left").reset_index(drop=False)
        return bounds_df

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        """
        Преобразует содержимое страницы в таблицу с данными транзакций

        :param bounds: границы ячеек
        :return: фрейм с транзакциями с этой страницы
        """
        df = pd.DataFrame(self.words)

        df["cell"] = df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        df = df.dropna(subset="cell").reset_index(drop=True)
        df["cell"] = df["cell"].astype(int)
        df["row"] = ((df["top"] - df["top"].shift(1)).abs() > 15).cumsum()

        df = self._group_df_to_records(df)
        df = df[df[self.pdf_columns[0]].str.match(r"^\d{2}\.\d{2}.*")].reset_index(drop=True)

        return df


class OzonBankTableExtractor(BaseTableExtractor):
    """
    Обработчик PDF-выписки из Ozon Банка

    Извлекает с каждой страницы содержимое таблицы с транзакциями и образует ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.OZON
    page_processor_class = OzonBankTablePageExtractor
    table_columns = (
        TableColumnEnum.date,
        TableColumnEnum.document_number,
        TableColumnEnum.details,
        TableColumnEnum.money_acc_curr,
        TableColumnEnum.money_op_curr,
    )

    def _update_merged_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Преобразует типы данных в объединённом фрейме, очищает невалидные значения
        и насыщает таблицу дополнительными данными из деталей транзакции

        :param df: исходный общий фрейм
        :return: итоговый общий фрейм
        """
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date], format="%d.%m.%Y %H:%M:%S", errors="coerce")

        df = self._update_money_amount_columns(df, additional_replacements=None)
        df[TableColumnEnum.details] = df[TableColumnEnum.details].str.replace(r"(\n|\s+)", " ", regex=True).str.strip()
        df[TableColumnEnum.order_number] = df[TableColumnEnum.details].str.extract(r"заказ . ([\d\-]+)")

        return df

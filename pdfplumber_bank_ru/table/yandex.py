from typing import List, Tuple

import pandas as pd
import numpy as np

from pdfplumber_bank_ru.commons.schemas import Word, CellBoundary
from pdfplumber_bank_ru.commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class YandexTablePageExtractor(BaseTablePageExtractor):
    """
    Обработчик одной страницы банковской выписки Яндекс Банка

    Извлекает содержимое страницы и преобразует в ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.YANDEX

    @property
    def pdf_columns(self) -> Tuple[str, ...]:
        return (
            "Описание операции",
            "Дата и время операции МСК",
            "Дата обработки МСК",
            "Карта",
            "Сумма в валюте операции",
            "Сумма в валюте ЭСП",
        )

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
        df = pd.DataFrame(self.words[: self.pdf_columns_word_count])

        df = df[(df["top"] == df["top"].min()) & (df["text"] == df["text"].str.capitalize())]
        df["cell"] = np.arange(df.shape[0])

        bounds_df = df.groupby("cell")["x0"].min().rename("left").reset_index(drop=False)
        right = bounds_df["left"].shift(-1).fillna(np.inf)
        bounds_df["left"] -= (80 - (right - bounds_df["left"])).mask(lambda x: x < 0, 0)
        return bounds_df

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        """
        Преобразует содержимое страницы в таблицу с данными транзакций

        :param bounds: границы ячеек
        :return: фрейм с транзакциями с этой страницы
        """

        df = pd.DataFrame(self.words[self.pdf_columns_word_count :])
        df["cell"] = df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)

        try:
            stop_before = df[(df["cell"] == 1) & (df["text"] == "Продолжение")].index[0]
            df = df.loc[: stop_before - 1, :]
        except IndexError:
            pass

        df["row"] = (df["x0"] == bounds[0].left).cumsum()
        df["row_max_cell"] = (df.groupby("row")["cell"].transform("max") + 1).astype(int)
        df["row"] = np.where(df["row_max_cell"] < self.pdf_columns_count, np.nan, df["row"])
        df["row"] = df["row"].ffill(axis=0).astype(np.uint32)

        df = self._group_df_to_records(df, rename_columns=False)
        if df.shape[1] == self.pdf_columns_count - 1:
            df.insert(3, 3.0, [np.nan] * df.shape[0])
        df.columns = self.pdf_columns
        df = df[df[self.pdf_columns[2]].str.match(r"(\d{2}\.){2}\d{4}")]

        return df


class YandexTableExtractor(BaseTableExtractor):
    """
    Обработчик PDF-выписки из Яндекс Банка

    Извлекает с каждой страницы содержимое таблицы с транзакциями и образует ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.YANDEX
    page_processor_class = YandexTablePageExtractor
    table_columns = (
        TableColumnEnum.details,
        TableColumnEnum.date,
        TableColumnEnum.date_performed,
        TableColumnEnum.card_number,
        TableColumnEnum.money_op_curr,
        TableColumnEnum.money_acc_curr,
    )

    def _update_merged_pages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Преобразует типы данных в объединённом фрейме, очищает невалидные значения
        и насыщает таблицу дополнительными данными из деталей транзакции

        :param df: исходный общий фрейм
        :return: итоговый общий фрейм
        """
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date], format="%d.%m.%Y в %H:%M", errors="coerce")
        df[TableColumnEnum.date_performed] = pd.to_datetime(
            df[TableColumnEnum.date_performed], format="%d.%m.%Y", errors="coerce"
        )
        df = df.dropna(subset=[TableColumnEnum.date])

        df = self._update_money_amount_columns(df, additional_replacements={"–": "-"})
        df[TableColumnEnum.details] = df[TableColumnEnum.details].str.replace(r"(\n|\s+)", " ", regex=True).str.strip()
        df[TableColumnEnum.service_name] = (
            df[TableColumnEnum.details]
            .str.extract(r"(YANDEX\s?[\.\*A-Z0-9]+)")
            .iloc[:, 0]
            .str.replace(r"[^A-Z]", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
        )

        return df

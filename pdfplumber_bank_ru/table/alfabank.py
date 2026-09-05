from typing import List, Tuple

import pandas as pd
import numpy as np

from commons.schemas import Word, CellBoundary
from commons.enums import BankNameEnum, TableColumnEnum
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

    def _get_cell_boundaries(self) -> List[CellBoundary]:
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
        if (determined_columns_count := bounds_df["left"].nunique()) != self.pdf_columns_count:
            raise ValueError(
                "number of columns does not match expected: {} != {}".format(determined_columns_count, self.pdf_columns_count)
            )
        bounds_df["right"] = bounds_df["left"].shift(-1).fillna(np.inf)
        return [CellBoundary(**bound) for bound in bounds_df.sort_values("cell")[["left", "right"]].to_dict(orient="records")]

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        """
        Преобразует содержимое страницы в таблицу с данными транзакций

        :param bounds: границы ячеек
        :return: фрейм с транзакциями с этой страницы
        """
        df = pd.DataFrame(self.words[self.pdf_columns_word_count :])
        df["cell"] = df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        df["row"] = (df["cell"] < df["cell"].shift(1)).cumsum()

        df = df.groupby(["row", "cell"])["text"].agg(lambda x: " ".join(x)).unstack("cell")
        df = df.reset_index(drop=True)
        df.columns = self.pdf_columns

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

        df[TableColumnEnum.money_acc_curr] = pd.to_numeric(
            df[TableColumnEnum.money_acc_curr].str.replace(r"[^0-9\-\.,]", "", regex=True).str.replace(",", "."),
            errors="coerce",
        )
        df[TableColumnEnum.card_number] = df[TableColumnEnum.details].str.extract(r"(2\d+\++\d+)")[0]

        return df

from typing import List, Tuple

import pandas as pd
import numpy as np

from commons.schemas import Word, CellBoundary
from commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class YandexTablePageExtractor(BaseTablePageExtractor):
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
        return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split())

    def _get_cell_boundaries(self) -> List[CellBoundary]:
        df = pd.DataFrame(self.words[: self.pdf_columns_word_count])
        df["item"] = np.arange(df.shape[0])

        df_columns = df[(df["top"] == df["top"].min()) & (df["text"] == df["text"].str.capitalize())]
        df_columns["cell"] = np.arange(df_columns.shape[0])

        bounds_df = df_columns.groupby("cell")["x0"].min().rename("left").reset_index(drop=False)
        if (determined_columns_count := bounds_df["left"].nunique()) != self.pdf_columns_count:
            raise ValueError(
                "number of columns does not match expected: {} != {}".format(determined_columns_count, self.pdf_columns_count)
            )
        bounds_df["right"] = bounds_df["left"].shift(-1).fillna(np.inf)
        bounds_df["left"] -= (80 - (bounds_df["right"] - bounds_df["left"])).mask(lambda x: x < 0, 0)
        bounds_df["right"] = bounds_df["left"].shift(-1).fillna(np.inf)

        return [CellBoundary(**bound) for bound in bounds_df.sort_values("cell")[["left", "right"]].to_dict(orient="records")]

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
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

        df = df.groupby(["row", "cell"])["text"].agg(lambda x: " ".join(x)).unstack("cell")
        df = df.reset_index(drop=True)
        if df.shape[1] == self.pdf_columns_count - 1:
            df.insert(3, 3.0, [np.nan] * df.shape[0])

        df.columns = self.pdf_columns

        df = df[df[self.pdf_columns[2]].str.match(r"(\d{2}\.){2}\d{4}")]

        return df.reset_index(drop=True)


class YandexTableExtractor(BaseTableExtractor):
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
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date], format="%d.%m.%Y в %H:%M", errors="coerce")
        df[TableColumnEnum.date_performed] = pd.to_datetime(
            df[TableColumnEnum.date_performed], format="%d.%m.%Y", errors="coerce"
        )
        df = df.dropna(subset=[TableColumnEnum.date])

        df[TableColumnEnum.currency] = df[TableColumnEnum.money_op_curr].str[-1]
        for col in [TableColumnEnum.money_op_curr, TableColumnEnum.money_acc_curr]:
            df[col] = pd.to_numeric(
                df[col].str.replace("–", "-").str.replace(r"[^-+,\.0-9]", "", regex=True).str.replace(",", "."),
                errors="coerce",
            )

        df[TableColumnEnum.details] = df[TableColumnEnum.details].str.replace(r"(\n|\s+)", " ", regex=True).str.strip()
        df[TableColumnEnum.service_name] = (
            df[TableColumnEnum.details]
            .str.extract(r"(YANDEX\s?[\.\*A-Z0-9]+)")
            .iloc[:, 0]
            .str.replace(r"[^A-Z]", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
        )

        return df

import re
from typing import List, Tuple

import pandas as pd
import numpy as np

from commons.schemas import Word, CellBoundary
from commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class OzonBankTablePageExtractor(BaseTablePageExtractor):
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
        try:
            return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split()[:2])
        except ValueError as e:
            if re.match(r"^(\d{2}\.){2}\d{4}$", (word := self.words[0]).text) and re.match(
                r"^(\d{2}:){2}\d{2}$", self.words[1].text
            ):
                return word, 0
            raise e

    def _get_cell_boundaries(self) -> List[CellBoundary]:
        if re.match(r"^(\d{2}\.){2}\d{4}$", self.words[0].text):
            raise ValueError("boundaries must be collected on the first page")

        df = pd.DataFrame(self.words)
        df = df[(df["x0"] == df["x0"].min()).cumsum() == 1]
        df = df[df["text"].str.capitalize() == df["text"]]
        df["cell"] = np.arange(df.shape[0])
        bounds_df = df.groupby("cell", sort=False)["x0"].min().rename("left").reset_index(drop=False)
        bounds_df["right"] = bounds_df["left"].shift(-1).fillna(np.inf)

        if bounds_df.shape[0] != self.pdf_columns_count:
            raise ValueError("number of columns does not match expected: {} != {}".format(df.shape[0], self.pdf_columns_count))
        return [CellBoundary(**bound) for bound in bounds_df.sort_values("cell")[["left", "right"]].to_dict(orient="records")]

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        words_df = pd.DataFrame(self.words)

        words_df["cell"] = words_df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        words_df = words_df.dropna(subset="cell").reset_index(drop=True)
        words_df["cell"] = words_df["cell"].astype(int)
        words_df["row"] = ((words_df["top"] - words_df["top"].shift(1)).abs() > 15).cumsum()

        words_df = words_df.groupby(["row", "cell"])["text"].agg(lambda x: " ".join(x)).unstack("cell")
        words_df.columns = self.pdf_columns
        words_df = words_df[words_df[self.pdf_columns[0]].str.match(r"^\d{2}\.\d{2}.*")].reset_index(drop=True)

        return words_df


class OzonBankTableExtractor(BaseTableExtractor):
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
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date], format="%d.%m.%Y %H:%M:%S", errors="coerce")

        df[TableColumnEnum.currency] = df[TableColumnEnum.money_op_curr].str[-1]
        for col in [TableColumnEnum.money_op_curr, TableColumnEnum.money_acc_curr]:
            df[col] = pd.to_numeric(df[col].str.replace(r"[^-+,\.0-9]", "", regex=True).str.replace(",", "."), errors="coerce")

        df[TableColumnEnum.details] = df[TableColumnEnum.details].str.replace(r"(\n|\s+)", " ", regex=True).str.strip()
        df[TableColumnEnum.order_number] = df[TableColumnEnum.details].str.extract(r"заказ . ([\d\-]+)")

        return df

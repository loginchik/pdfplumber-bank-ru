from typing import List, Tuple

import pandas as pd
import numpy as np

from commons.schemas import Word, CellBoundary
from commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class TBankTablePageExtractor(BaseTablePageExtractor):
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
        return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split()[:-1])

    def _get_cell_boundaries(self) -> List[CellBoundary]:
        df = pd.DataFrame(self.words[: self.pdf_columns_word_count])
        df["cell"] = ((df["x0"].astype(int) == df["x0"]).cumsum() - 1) % self.pdf_columns_count

        bounds_df = df.groupby("cell", sort=False)["x0"].min().rename("left").reset_index(drop=False)
        if (determined_columns_count := bounds_df["left"].nunique()) != self.pdf_columns_count:
            raise ValueError(
                "number of columns does not match expected: {} != {}".format(determined_columns_count, self.pdf_columns_count)
            )
        bounds_df["right"] = bounds_df["left"].shift(-1).fillna(np.inf)
        return [CellBoundary(**bound) for bound in bounds_df.sort_values("cell")[["left", "right"]].to_dict(orient="records")]

    def words_to_frame(self, bounds: List[CellBoundary]) -> pd.DataFrame:
        words_df = pd.DataFrame(self.words[self.pdf_columns_word_count :])

        words_df["cell"] = words_df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        words_df = words_df.dropna(subset="cell").reset_index(drop=True)
        words_df["cell"] = words_df["cell"].astype(int)
        words_df["row"] = (words_df["cell"] == 0).cumsum() - 1

        words_df = words_df.groupby(["row", "cell"])["text"].agg(lambda x: " ".join(x)).unstack("cell")
        words_df.columns = list(self.pdf_columns)
        words_df = words_df[words_df[self.pdf_columns[0]].str.match(r"^\d{2}.\d{2}(.\d{4})?$")].reset_index(drop=False)

        words_df["row"] = np.where(words_df[self.pdf_columns[0]].str.match(r"^\d{2}\:\d{2}"), np.nan, words_df["row"])
        words_df["row"] = words_df["row"].ffill()
        words_df = words_df.groupby("row").agg(lambda x: " ".join(x.dropna())).reset_index(drop=True)
        return words_df


class TBankTableExtractor(BaseTableExtractor):
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
        return df

from typing import List, Tuple

import pandas as pd
import numpy as np

from commons.schemas import Word, CellBoundary
from commons.enums import BankNameEnum, TableColumnEnum
from .base import BaseTablePageExtractor, BaseTableExtractor


class RaiffeisenTablePageExtractor(BaseTablePageExtractor):
    """
    Обработчик одной страницы банковской выписки Райффайзенбанка

    Извлекает содержимое страницы и преобразует в ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.RAIF

    @property
    def pdf_columns(self) -> Tuple[str, ...]:
        return (
            "Дата операции",
            "Номер документа",
            "Сумма операции в валюте операции",
            "Сумма операции в валюте счета",
            "Детали операции",
            "Номер карты",
        )

    def _locate_table(self) -> Tuple[Word, int]:
        """
        Определяет начало таблицы по полному названию первой колонки

        :return: координаты первой ячейки таблицы
        """
        return self._get_first_cell(words=self.words, target_words=self.pdf_columns[0].split()[:2])

    def _get_cell_boundaries(self) -> List[CellBoundary]:
        """
        Определяет границы ячеек искомой таблицы

        :return: границы ячеек в таблице слева направо
        :raise ValueError:
        """
        df = pd.DataFrame(self.words[: self.pdf_columns_word_count])
        df = df[(df["text"].str.capitalize() == df["text"])].drop_duplicates(subset="x0", keep="first")
        df["cell"] = np.arange(df.shape[0])

        bounds_df = df.groupby("cell", sort=False)["x0"].min().rename("left").reset_index(drop=False)
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
        words_df = pd.DataFrame(self.words[self.pdf_columns_word_count :])

        words_df["cell"] = words_df.apply(lambda row: self.bound_to_cell(row, bounds), axis=1)
        words_df = words_df.dropna(subset="cell").reset_index(drop=True)
        words_df["cell"] = words_df["cell"].astype(int)
        words_df["row"] = ((words_df["top"] - words_df["top"].shift(1)).abs() > 15).cumsum()

        words_df = words_df.groupby(["row", "cell"])["text"].agg(lambda x: " ".join(x)).unstack("cell")
        words_df.columns = self.pdf_columns
        words_df = words_df[words_df[self.pdf_columns[0]].str.match(r"^\d{2}\.\d{2}.*")].reset_index(drop=True)

        return words_df


class RaiffeisenTableExtractor(BaseTableExtractor):
    """
    Обработчик PDF-выписки из Райффайзенбанка

    Извлекает с каждой страницы содержимое таблицы с транзакциями и образует ``pandas.DataFrame``
    """

    BANK_NAME = BankNameEnum.RAIF
    page_processor_class = RaiffeisenTablePageExtractor
    table_columns = (
        TableColumnEnum.date,
        TableColumnEnum.document_number,
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
        df[[TableColumnEnum.date, TableColumnEnum.date_performed]] = (
            df[TableColumnEnum.date].str.extract(r"(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}) (.+)").apply(pd.Series)
        )
        df[TableColumnEnum.date] = pd.to_datetime(df[TableColumnEnum.date].str.strip(), format="%d.%m.%Y %H:%M")
        df[TableColumnEnum.date_performed] = pd.to_datetime(
            df[TableColumnEnum.date_performed].str.strip(), format="%d.%m.%Y", errors="coerce"
        )
        df = df.dropna(subset=[TableColumnEnum.date])

        df[TableColumnEnum.currency] = df[TableColumnEnum.money_op_curr].str[-1]
        for col in [TableColumnEnum.money_op_curr, TableColumnEnum.money_acc_curr]:
            df[col] = pd.to_numeric(df[col].str.replace(r"[^-+,0-9]", "", regex=True).str.replace(",", "."), errors="coerce")

        df[TableColumnEnum.details] = df[TableColumnEnum.details].str.replace(r"(\n|\s+)", " ", regex=True).str.strip()
        df[TableColumnEnum.from_account] = df[TableColumnEnum.details].str.extract(r"Со сч[ёе]та\: (\d*\**\d+)")
        df[TableColumnEnum.to_account] = df[TableColumnEnum.details].str.extract(r"На сч[ёе]т\: (\d*\**\d+)")
        df[TableColumnEnum.to_account] = df[TableColumnEnum.to_account].fillna(
            df[TableColumnEnum.details].str.extract(r"номер счета получателя\s?\-\s?(\d+)").iloc[:, 0]
        )

        df[TableColumnEnum.card_number] = df[TableColumnEnum.card_number].str.strip().mask(lambda s: s == "", np.nan)
        df[TableColumnEnum.document_number] = df[TableColumnEnum.document_number].str.strip().mask(lambda s: s == "", np.nan)

        return df

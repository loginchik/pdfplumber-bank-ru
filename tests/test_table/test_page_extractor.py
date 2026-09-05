from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Union

import pandas as pd
import pdfplumber
import pytest

from pdfplumber_bank_ru.table.alfabank import AlfaBankTablePageExtractor
from pdfplumber_bank_ru.table.tbank import TBankTablePageExtractor
from pdfplumber_bank_ru.table.raiffeisen import RaiffeisenTablePageExtractor
from pdfplumber_bank_ru.table.ozonbank import OzonBankTablePageExtractor
from pdfplumber_bank_ru.table.yandex import YandexTablePageExtractor


class TestPageExtractorBase(ABC):
    __test__ = False

    filename: str = None
    extractor_class: Union[AlfaBankTablePageExtractor, TBankTablePageExtractor, RaiffeisenTablePageExtractor] = None

    @pytest.fixture(autouse=True)
    def setup_method(self, test_data_dir: Path) -> None:
        test_file_1 = test_data_dir / self.filename

        with pdfplumber.open(test_file_1) as pdf:
            self.extractor_1 = self.extractor_class(page=pdf.pages[0])
            self.extractor_2 = self.extractor_class(page=pdf.pages[1])

    @abstractmethod
    def test_properties(self) -> None: ...

    @abstractmethod
    def test_get_first_cell(self) -> None: ...

    def test_get_cell_boundaries(self) -> None:
        self.extractor_1.locate_table()
        bounds_1 = self.extractor_1._get_cell_boundaries()
        assert len(bounds_1) == len(self.extractor_1.pdf_columns)

        self.extractor_2.locate_table()
        bounds_2 = self.extractor_2._get_cell_boundaries()
        assert len(bounds_2) == len(self.extractor_2.pdf_columns)

        assert all(b1 == b2 for b1, b2 in zip(bounds_1, bounds_2))

    def test_convert_to_frame(self) -> None:
        df_1 = self.extractor_1.convert_to_frame()
        df_2 = self.extractor_2.convert_to_frame()

        assert isinstance(df_1, pd.DataFrame)
        assert isinstance(df_2, pd.DataFrame)

        assert df_1.shape[1] == self.extractor_1.pdf_columns_count
        assert df_2.shape[1] == self.extractor_2.pdf_columns_count

        assert df_1.isna().sum().sum() == 0
        assert df_2.isna().sum().sum() == 0


class TestAlfaBankPageExtractor(TestPageExtractorBase):
    __test__ = True
    filename = "alfabank_1.pdf"
    extractor_class = AlfaBankTablePageExtractor

    def test_properties(self) -> None:
        assert self.extractor_1.pdf_columns_word_count == 9
        assert self.extractor_2.pdf_columns_word_count == 9

    def test_get_first_cell(self) -> None:
        words_before = len(self.extractor_1.words)
        first_cell = self.extractor_1.locate_table()
        assert first_cell.text == "Дата"
        assert 0 < words_before - len(self.extractor_1.words) < 90

        words_before = len(self.extractor_2.words)
        first_cell = self.extractor_2.locate_table()
        assert first_cell.text == "Дата"
        assert len(self.extractor_2.words) == words_before


class TestTBankPageExtractor(TestPageExtractorBase):
    __test__ = True
    filename = "tbank_1.pdf"
    extractor_class = TBankTablePageExtractor

    def test_properties(self) -> None:
        assert self.extractor_1.pdf_columns_word_count == 19
        assert self.extractor_2.pdf_columns_word_count == 19

    def test_get_first_cell(self) -> None:
        words_before = len(self.extractor_1.words)
        first_cell = self.extractor_1.locate_table()
        assert first_cell.text == "Дата"
        assert 0 < words_before - len(self.extractor_1.words) < 80

        words_before = len(self.extractor_2.words)
        first_cell = self.extractor_2.locate_table()
        assert first_cell.text == "Дата"
        assert len(self.extractor_2.words) == words_before


class TestRaiffeisenPageExtractor(TestPageExtractorBase):
    __test__ = True
    filename = "raiffeisen_1.pdf"
    extractor_class = RaiffeisenTablePageExtractor

    def test_properties(self) -> None:
        assert self.extractor_1.pdf_columns_word_count == 18
        assert self.extractor_2.pdf_columns_word_count == 18

    def test_get_first_cell(self) -> None:
        words_before = len(self.extractor_1.words)
        first_cell = self.extractor_1.locate_table()
        assert first_cell.text == "Дата"
        assert 0 < words_before - len(self.extractor_1.words) < 80

        words_before = len(self.extractor_2.words)
        first_cell = self.extractor_2.locate_table()
        assert first_cell.text == "Дата"
        assert 0 < words_before - len(self.extractor_2.words) < 30

    def test_convert_to_frame(self) -> None:
        df_1 = self.extractor_1.convert_to_frame()
        df_2 = self.extractor_2.convert_to_frame()

        assert isinstance(df_1, pd.DataFrame)
        assert isinstance(df_2, pd.DataFrame)

        assert df_1.shape[1] == self.extractor_1.pdf_columns_count
        assert df_2.shape[1] == self.extractor_2.pdf_columns_count
        assert df_2.shape[0] > df_1.shape[0]

        assert df_1.iloc[:, :-1].isna().sum().sum() == 0
        assert df_2.iloc[:, :-1].isna().sum().sum() == 0


class TestOzonBankPageExtractor(TestPageExtractorBase):
    __test__ = True
    filename = "ozon_1.pdf"
    extractor_class = OzonBankTablePageExtractor

    def test_properties(self) -> None:
        assert self.extractor_1.pdf_columns_word_count == 14
        assert self.extractor_2.pdf_columns_word_count == 14

    def test_get_first_cell(self) -> None:
        words_before = len(self.extractor_1.words)
        first_cell = self.extractor_1.locate_table()
        assert first_cell.text == "Дата"
        assert 0 < words_before - len(self.extractor_1.words) < 80

        words_before = len(self.extractor_2.words)
        first_cell = self.extractor_2.locate_table()
        assert re.match(r"^(\d{2}\.){2}\d{4}$", first_cell.text) is not None
        assert words_before == len(self.extractor_2.words)

    def test_get_cell_boundaries(self) -> None:
        self.extractor_1.locate_table()
        bounds_1 = self.extractor_1._get_cell_boundaries()
        assert len(bounds_1) == len(self.extractor_1.pdf_columns)

        self.extractor_2.locate_table()
        with pytest.raises(ValueError):
            self.extractor_2._get_cell_boundaries()

    def test_convert_to_frame(self) -> None:
        df_1 = self.extractor_1.convert_to_frame()
        df_2 = self.extractor_2.convert_to_frame(boundaries=self.extractor_1._get_cell_boundaries())

        assert isinstance(df_1, pd.DataFrame)
        assert isinstance(df_2, pd.DataFrame)

        assert df_1.shape[1] == self.extractor_1.pdf_columns_count
        assert df_2.shape[1] == self.extractor_2.pdf_columns_count
        assert df_2.shape[0] > df_1.shape[0]

        assert df_1.isna().sum().sum() == 0
        assert df_2.isna().sum().sum() == 0


class TestYandexPageExtractor(TestPageExtractorBase):
    __test__ = True
    filename = "yandex_1.pdf"
    extractor_class = YandexTablePageExtractor

    def test_properties(self) -> None:
        assert self.extractor_1.pdf_columns_word_count == 19
        assert self.extractor_2.pdf_columns_word_count == 19

    def test_get_first_cell(self) -> None:
        words_before = len(self.extractor_1.words)
        first_cell = self.extractor_1.locate_table()
        assert first_cell.text == "Описание"
        assert 0 < words_before - len(self.extractor_1.words) < 80

        words_before = len(self.extractor_2.words)
        first_cell = self.extractor_2.locate_table()
        assert first_cell.text == "Описание"
        assert words_before - len(self.extractor_2.words) == 0

    def test_convert_to_frame(self) -> None:
        df_1 = self.extractor_1.convert_to_frame()
        df_2 = self.extractor_2.convert_to_frame()

        assert isinstance(df_1, pd.DataFrame)
        assert isinstance(df_2, pd.DataFrame)

        assert df_1.shape[1] == self.extractor_1.pdf_columns_count
        assert df_2.shape[1] == self.extractor_2.pdf_columns_count

        assert df_1.iloc[:, [0, 1, 2, 4, 5]].isna().sum().sum() == 0
        assert df_2.iloc[:, [0, 1, 2, 4, 5]].isna().sum().sum() == 0

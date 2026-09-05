import datetime as dt
from pathlib import Path
from typing import Union

import pdfplumber
import pytest

from pdfplumber_bank_ru.metadata.base import Metadata
from pdfplumber_bank_ru.metadata.tbank import TBankMetadataExtractor
from pdfplumber_bank_ru.metadata.raiffeisen import RaiffeisenMetadataExtractor


class TestMetadataExtractorBase:
    __test__ = False
    filename: str = None
    extractor_class: Union[TBankMetadataExtractor] = None

    @pytest.fixture(autouse=True)
    def setup_method(self, test_data_dir: Path) -> None:
        self.test_file_1 = test_data_dir / self.filename
        self.extractor = self.extractor_class()

        with pdfplumber.open(self.test_file_1) as pdf:
            self.words_per_page = {page_num: self.extractor.get_words(page) for page_num, page in enumerate(pdf.pages)}

    def test_extract_from_file(self) -> None:
        value = self.extractor.extract_from_file(self.test_file_1)
        assert isinstance(value, Metadata)
        assert value.bank_name == self.extractor_class.BANK_NAME

    def test_get_account_number(self) -> None:
        value = self.extractor.get_account_number(self.words_per_page)
        assert isinstance(value, int)
        assert len(str(value)) == 20

    def test_get_issued_date(self) -> None:
        value = self.extractor.get_issued_date(self.words_per_page)
        assert isinstance(value, dt.date)

    def test_get_period(self) -> None:
        value = self.extractor.get_period(self.words_per_page)
        assert isinstance(value, tuple)
        assert len(value) == 2
        assert all(isinstance(x, dt.date) for x in value)
        assert value[0] <= value[1]

    def test_get_owner_name(self) -> None:
        value = self.extractor.get_owner_name(self.words_per_page)
        assert isinstance(value, str)


class TestTBankMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "tbank_1.pdf"
    extractor_class = TBankMetadataExtractor


class TestRaiffeisenMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "raiffeisen_1.pdf"
    extractor_class = RaiffeisenMetadataExtractor

import datetime as dt
from pathlib import Path
from typing import Union

import pdfplumber
import pytest

from pdfplumber_bank_ru.commons.schemas import Word
from pdfplumber_bank_ru.metadata.base import Metadata, BaseMetadataExtractor
from pdfplumber_bank_ru.metadata.tbank import TBankMetadataExtractor
from pdfplumber_bank_ru.metadata.raiffeisen import RaiffeisenMetadataExtractor
from pdfplumber_bank_ru.metadata.alfabank import AlfaBankMetadataExtractor
from pdfplumber_bank_ru.metadata.ozonbank import OzonBankMetadataExtractor
from pdfplumber_bank_ru.metadata.yandex import YandexMetadataExtractor


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


class TestBaseMetadataExtractor:
    @pytest.mark.parametrize("collocation", ["this is text", "another text", "another one"])
    @pytest.mark.parametrize("before", list(range(1, 10, 2)))
    def test_look_up_collocation_success(self, collocation: str, before: int) -> None:
        words = [Word(text="a", x0=0.0, x1=1.0, top=1.0)] * before
        words += [Word(text=w, x0=0.0, x1=1.0, top=1.0) for w in collocation.split()]
        words += [Word(text="a", x0=0.0, x1=1.0, top=1.0)] * 10

        result = BaseMetadataExtractor._look_up_collocation(collocation, words)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(r, int) for r in result)

        assert result[0] == before
        assert result[1] == before + len(collocation.split())

    def test_get_related_words_in_line(self) -> None:
        words = [Word(text="a", x0=i, x1=i + 0.5, top=1) for i in range(10)]
        words += [Word(text="b", x0=i, x1=i + 0.5, top=1) for i in range(15, 25)]
        words += [Word(text="c", x0=i, x1=i + 0.5, top=2) for i in range(10)]

        result = BaseMetadataExtractor._get_related_words_in_line(words, x_tolerance=3)
        assert isinstance(result, list)
        assert len(result) == 10
        assert "".join(w.text for w in result) == "a" * 10


class TestTBankMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "tbank_1.pdf"
    extractor_class = TBankMetadataExtractor


class TestRaiffeisenMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "raiffeisen_1.pdf"
    extractor_class = RaiffeisenMetadataExtractor

    def test_get_account_number(self) -> None:
        value = self.extractor.get_account_number(self.words_per_page)
        assert isinstance(value, int)
        assert len(str(value)) == 20
        assert any(str(value).startswith(x) for x in ["407", "408"])


class TestAlfaBankMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "alfabank_1.pdf"
    extractor_class = AlfaBankMetadataExtractor

    def test_get_account_number(self) -> None:
        value = self.extractor.get_account_number(self.words_per_page)
        assert isinstance(value, int)
        assert len(str(value)) == 20
        assert any(str(value).startswith(x) for x in ["407", "408"])


class TestOzonBankMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "ozon_1.pdf"
    extractor_class = OzonBankMetadataExtractor

    def test_get_account_number(self) -> None:
        value = self.extractor.get_account_number(self.words_per_page)
        assert isinstance(value, int)
        assert len(str(value)) == 20
        assert any(str(value).startswith(x) for x in ["407", "408"])


class TestYandexMetadataExtractor(TestMetadataExtractorBase):
    __test__ = True
    filename = "yandex_1.pdf"
    extractor_class = YandexMetadataExtractor

    def test_get_account_number(self) -> None:
        value = self.extractor.get_account_number(self.words_per_page)
        assert isinstance(value, int)
        assert len(str(value)) == 17

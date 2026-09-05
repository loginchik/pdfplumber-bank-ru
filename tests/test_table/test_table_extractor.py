from abc import ABC
from pathlib import Path
from typing import Union

import pandas as pd
import pytest

from pdfplumber_bank_ru.table.alfabank import AlfaBankTableExtractor
from pdfplumber_bank_ru.table.ozonbank import OzonBankTableExtractor
from pdfplumber_bank_ru.table.raiffeisen import RaiffeisenTableExtractor
from pdfplumber_bank_ru.table.tbank import TBankTableExtractor
from pdfplumber_bank_ru.table.yandex import YandexTableExtractor


class TestTableExtractorBase(ABC):
    __test__ = False

    filename: str = None
    processor_class: Union[TBankTableExtractor]

    @pytest.fixture(autouse=True)
    def setup_method(self, test_data_dir: Path) -> None:
        self.test_file_1 = test_data_dir / self.filename
        self.processor = self.processor_class()

    def test_extract_from_file(self) -> None:
        df = self.processor.extract_from_file(self.test_file_1)
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] > 0
        assert all(isinstance(x, str) for x in df.columns)


class TestAlfabankTableExtractor(TestTableExtractorBase):
    __test__ = True
    filename = "alfabank_1.pdf"
    processor_class = AlfaBankTableExtractor


class TestOzonBankTableExtractor(TestTableExtractorBase):
    __test__ = True
    filename = "ozon_1.pdf"
    processor_class = OzonBankTableExtractor


class TestRaiffeisenbankTableExtractor(TestTableExtractorBase):
    __test__ = True
    filename = "raiffeisen_1.pdf"
    processor_class = RaiffeisenTableExtractor


class TestTBankTableExtractor(TestTableExtractorBase):
    __test__ = True
    filename = "tbank_1.pdf"
    processor_class = TBankTableExtractor


class TestYandexTableExtractor(TestTableExtractorBase):
    __test__ = True
    filename = "yandex_1.pdf"
    processor_class = YandexTableExtractor

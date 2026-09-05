from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime as dt
from pathlib import Path
from typing import Tuple, Dict, List

import pdfplumber
from pdfplumber.pdf import PDF

from commons.base import BasicProcessor
from commons.enums import BankNameEnum
from commons.schemas import Word


@dataclass(frozen=True)
class Metadata:
    owner_name: str
    account_number: int
    bank_name: BankNameEnum
    issued_date: dt.date
    period: Tuple[dt.date, dt.date]


class BaseMetadataExtractor(ABC, BasicProcessor):
    BANK_NAME: BankNameEnum = None

    def extract_from_file(self, filepath: Path) -> Metadata:
        with pdfplumber.open(filepath) as pdf:
            return self.extract_from_pdf(pdf)

    def extract_from_pdf(self, pdf: PDF) -> Metadata:
        words_per_page = {page_num: self.get_words(page) for page_num, page in enumerate(pdf.pages)}

        return Metadata(
            account_number=self.get_account_number(words_per_page),
            issued_date=self.get_issued_date(words_per_page),
            owner_name=self.get_owner_name(words_per_page),
            period=self.get_period(words_per_page),
            bank_name=self.BANK_NAME,
        )

    @abstractmethod
    def get_account_number(self, words_per_page: Dict[int, List[Word]]) -> int: ...

    @abstractmethod
    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date: ...

    @abstractmethod
    def get_owner_name(self, words_per_page: Dict[int, List[Word]]) -> str: ...

    @abstractmethod
    def get_period(self, words_per_page: Dict[int, List[Word]]) -> Tuple[dt.date, dt.date]: ...

    @staticmethod
    def _look_up_collocation(collocation: str, words: List[Word]) -> int:
        collocation_words = collocation.split(" ")

        for i, word in enumerate(words):
            if word.text == collocation_words[0]:
                possible_collocation = " ".join([w.text for w in words[i : i + len(collocation_words)]])
                if possible_collocation == collocation:
                    return i

        raise IndexError(f"collocation '{collocation}' no found in words")

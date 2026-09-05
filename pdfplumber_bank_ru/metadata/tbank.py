import datetime as dt
from typing import Dict, List, Tuple

from commons.enums import BankNameEnum
from commons.schemas import Word
from .base import BaseMetadataExtractor


class TBankMetadataExtractor(BaseMetadataExtractor):
    BANK_NAME = BankNameEnum.TBANK

    def get_account_number(self, words_per_page: Dict[int, List[Word]]) -> int:
        words_first_page = words_per_page[0]
        try:
            collocation_start_i = self._look_up_collocation("Номер лицевого счета:", words_first_page)
        except IndexError as e:
            raise IndexError("no account number found on first page") from e

        account_number = words_first_page[collocation_start_i + 3]
        return int(account_number.text)

    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date:
        words_first_page = words_per_page[0]
        try:
            collocation_start_i = self._look_up_collocation("Исх. №", words_first_page)
        except IndexError as e:
            raise IndexError("no issued date found on first page") from e

        issued_date = words_first_page[collocation_start_i + 3]
        return dt.datetime.strptime(issued_date.text, "%d.%m.%Y").date()

    def get_owner_name(self, words_per_page: Dict[int, List[Word]]) -> str:
        words_first_page = words_per_page[0]

        try:
            issued_date_i = self._look_up_collocation("Исх. №", words_first_page) + 3
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        try:
            address_start_i = self._look_up_collocation("Адрес места жительства:", words_first_page)
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        owner_name = " ".join([w.text for w in words_first_page[issued_date_i:address_start_i]])
        return owner_name

    def get_period(self, words_per_page: Dict[int, List[Word]]) -> Tuple[dt.date, dt.date]:
        words_first_page = words_per_page[0]

        try:
            collocation_start_i = self._look_up_collocation("Движение средств за период с", words_first_page)
        except IndexError as e:
            raise IndexError("no period found on first page") from e

        start_date = words_first_page[collocation_start_i + 5]
        end_date = words_first_page[collocation_start_i + 7]

        start_date = dt.datetime.strptime(start_date.text, "%d.%m.%Y").date()
        end_date = dt.datetime.strptime(end_date.text, "%d.%m.%Y").date()
        return start_date, end_date

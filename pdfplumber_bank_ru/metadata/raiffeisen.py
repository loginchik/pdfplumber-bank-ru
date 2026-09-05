import datetime as dt
from typing import Dict, List, Tuple

from commons.enums import BankNameEnum
from commons.schemas import Word
from .base import BaseMetadataExtractor


class RaiffeisenMetadataExtractor(BaseMetadataExtractor):
    BANK_NAME = BankNameEnum.RAIF

    def get_account_number(self, words_per_page: Dict[int, List[Word]]) -> int:
        current_words = words_per_page[0]
        try:
            label_i = self._look_up_collocation("Номер счета", current_words)
        except IndexError as e:
            raise IndexError("no account number found on first page") from e

        label = current_words[label_i]
        current_words = current_words[label_i + 1 :]

        value_start_i = next(i for i, word in enumerate(current_words) if word.x0 == label.x0)

        value_words = [current_words[value_start_i]]
        current_words = current_words[value_start_i + 1 :]
        for word in current_words:
            if word.top == value_words[0].top:
                value_words.append(word)
            else:
                break

        account_number = int("".join(w.text for w in value_words))
        return account_number

    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date:
        current_words = words_per_page[0]
        try:
            collocation_start_i = self._look_up_collocation("Дата выдачи:", current_words)
        except IndexError as e:
            raise IndexError("no issued date found on first page") from e

        issued_date = current_words[collocation_start_i + 2]
        return dt.datetime.strptime(issued_date.text, "%d.%m.%Y").date()

    def get_owner_name(self, words_per_page: Dict[int, List[Word]]) -> str:
        current_words = words_per_page[0]

        try:
            label_i = self._look_up_collocation("Клиент", current_words)
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        label = current_words[label_i]
        current_words = current_words[label_i + 1 :]

        name_start_i = next(i for i, word in enumerate(current_words) if word.x0 == label.x0)
        name_words = [current_words[name_start_i]]

        current_words = current_words[name_start_i + 1 :]
        for word in current_words:
            if word.x0 - name_words[-1].x1 < 3:
                name_words.append(word)
            else:
                break

        owner_name = " ".join(w.text for w in name_words)
        return owner_name

    def get_period(self, words_per_page: Dict[int, List[Word]]) -> Tuple[dt.date, dt.date]:
        words_first_page = words_per_page[0]

        try:
            collocation_start_i = self._look_up_collocation("Период:", words_first_page)
        except IndexError as e:
            raise IndexError("no period found on first page") from e

        start_date = words_first_page[collocation_start_i + 2]
        end_date = words_first_page[collocation_start_i + 4]

        start_date = dt.datetime.strptime(start_date.text, "%d.%m.%Y").date()
        end_date = dt.datetime.strptime(end_date.text, "%d.%m.%Y").date()
        return start_date, end_date

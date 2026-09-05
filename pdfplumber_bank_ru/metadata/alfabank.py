import datetime as dt
from typing import Dict, List, Tuple

from commons.enums import BankNameEnum
from commons.schemas import Word
from .base import BaseMetadataExtractor


class AlfaBankMetadataExtractor(BaseMetadataExtractor):
    """
    Обработчик метаданных для выписки из Альфа-Банка
    """

    BANK_NAME = BankNameEnum.ALFA

    def get_account_number(self, words_per_page: Dict[int, List[Word]]) -> int:
        """
        Извлекает с первой страницы выписки номер счёта

        :param words_per_page: слова с первой страницы
        :return: номер счёта
        :raise IndexError: номер счёта не найден
        """
        current_words = words_per_page[0]
        try:
            _, label_i_end = self._look_up_collocation("Номер счета", current_words)
        except IndexError as e:
            raise IndexError("no account number found on first page") from e

        account_number = int(current_words[label_i_end].text)
        return account_number

    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date:
        """
        Извлекает с первой страницы выписки дату формирования документа

        :param words_per_page: слова с первой страницы
        :return: дата формирования выписки
        :raise IndexError: дата формирования выписки не найдена
        """
        current_words = words_per_page[0]
        try:
            _, collocation_end_i = self._look_up_collocation("Дата формирования", current_words)
        except IndexError as e:
            raise IndexError("no issued date found on first page") from e

        issued_date = current_words[collocation_end_i]
        return dt.datetime.strptime(issued_date.text, "%d.%m.%Y").date()

    def get_owner_name(self, words_per_page: Dict[int, List[Word]]) -> str:
        """
        Извлекает с первой страницы выписки имя владельца счёта

        :param words_per_page: слова с первой страницы
        :return: имя владельца счёта
        :raise IndexError: имя владельца счёта не найдена
        """
        current_words = words_per_page[0]

        try:
            _, label_i_end = self._look_up_collocation("Клиент", current_words)
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        current_words = current_words[label_i_end:]

        name_words = [current_words[0]]
        current_words = current_words[1:]
        for word in current_words:
            if word.top == name_words[0].top and word.x0 - name_words[-1].x1 < 3:
                name_words.append(word)
            else:
                break

        owner_name = " ".join(w.text for w in name_words)
        return owner_name

    def get_period(self, words_per_page: Dict[int, List[Word]]) -> Tuple[dt.date, dt.date]:
        """
        Извлекает с первой страницы выписки промежуток дат,
        транзакции за который включены в документ

        :param words_per_page: слова с первой страницы
        :return: период выписки
        :raise IndexError: даты периода выписки не найдены
        """
        current_words = words_per_page[0]
        try:
            _, collocation_end_i = self._look_up_collocation("За период с", current_words)
        except IndexError as e:
            raise IndexError("no period found on first page") from e

        start_date = current_words[collocation_end_i]
        end_date = current_words[collocation_end_i + 2]

        start_date = dt.datetime.strptime(start_date.text, "%d.%m.%Y").date()
        end_date = dt.datetime.strptime(end_date.text, "%d.%m.%Y").date()
        return start_date, end_date

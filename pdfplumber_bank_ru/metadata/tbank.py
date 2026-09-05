import datetime as dt
from typing import Dict, List, Tuple

from commons.enums import BankNameEnum
from commons.schemas import Word
from .base import BaseMetadataExtractor


class TBankMetadataExtractor(BaseMetadataExtractor):
    """
    Обработчик метаданных для выписки из ТБанка
    """

    BANK_NAME = BankNameEnum.TBANK

    def get_account_number(self, words_per_page: Dict[int, List[Word]]) -> int:
        """
        Извлекает с первой страницы выписки номер счёта

        :param words_per_page: слова с первой страницы
        :return: номер счёта
        :raise IndexError: номер счёта не найден
        """
        words_first_page = words_per_page[0]
        try:
            _, collocation_end_i = self._look_up_collocation("Номер лицевого счета:", words_first_page)
        except IndexError as e:
            raise IndexError("no account number found on first page") from e

        account_number = words_first_page[collocation_end_i]
        return int(account_number.text)

    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date:
        """
        Извлекает с первой страницы выписки дату формирования документа

        :param words_per_page: слова с первой страницы
        :return: дата формирования выписки
        :raise IndexError: дата формирования выписки не найдена
        """
        words_first_page = words_per_page[0]
        try:
            _, collocation_end_i = self._look_up_collocation("Исх. №", words_first_page)
        except IndexError as e:
            raise IndexError("no issued date found on first page") from e

        issued_date = words_first_page[collocation_end_i + 1]
        return dt.datetime.strptime(issued_date.text, "%d.%m.%Y").date()

    def get_owner_name(self, words_per_page: Dict[int, List[Word]]) -> str:
        """
        Извлекает с первой страницы выписки имя владельца счёта

        :param words_per_page: слова с первой страницы
        :return: имя владельца счёта
        :raise IndexError: имя владельца счёта не найдена
        """
        words_first_page = words_per_page[0]

        try:
            _, issued_date_end_i = self._look_up_collocation("Исх. №", words_first_page)
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        try:
            address_start_i, _ = self._look_up_collocation("Адрес места жительства:", words_first_page)
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        owner_name = " ".join([w.text for w in words_first_page[issued_date_end_i + 2 : address_start_i]])
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
            _, collocation_end_i = self._look_up_collocation("Движение средств за период с", current_words)
        except IndexError as e:
            raise IndexError("no period found on first page") from e

        start_date = current_words[collocation_end_i]
        end_date = current_words[collocation_end_i + 2]

        start_date = dt.datetime.strptime(start_date.text, "%d.%m.%Y").date()
        end_date = dt.datetime.strptime(end_date.text, "%d.%m.%Y").date()
        return start_date, end_date

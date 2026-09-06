import datetime as dt
from typing import Dict, List, Tuple

from pdfplumber_bank_ru.commons.enums import BankNameEnum
from pdfplumber_bank_ru.commons.schemas import Word
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
        return self._get_account_number(words_per_page[0], "Номер лицевого счета:")

    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date:
        """
        Извлекает с первой страницы выписки дату формирования документа

        :param words_per_page: слова с первой страницы
        :return: дата формирования выписки
        :raise IndexError: дата формирования выписки не найдена
        """
        return self._get_issued_date(words_per_page[0], "Исх. №", 1)

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
        return self._get_period(words_per_page[0], "Движение средств за период с")

import datetime as dt
from typing import Dict, List, Tuple

from commons.enums import BankNameEnum
from commons.schemas import Word
from .base import BaseMetadataExtractor


class RaiffeisenMetadataExtractor(BaseMetadataExtractor):
    """
    Обработчик метаданных для выписки из Райффайзенбанка
    """

    BANK_NAME = BankNameEnum.RAIF

    def get_account_number(self, words_per_page: Dict[int, List[Word]]) -> int:
        """
        Извлекает с первой страницы выписки номер счёта

        :param words_per_page: слова с первой страницы
        :return: номер счёта
        :raise IndexError: номер счёта не найден
        """
        current_words = words_per_page[0]
        try:
            label_start_i, label_end_i = self._look_up_collocation("Номер счета", current_words)
        except IndexError as e:
            raise IndexError("no account number found on first page") from e

        label = current_words[label_start_i]
        current_words = current_words[label_end_i:]

        value_start_i = next(i for i, word in enumerate(current_words) if word.x0 == label.x0)
        value_words = self._get_related_words_in_line(current_words[value_start_i:])

        account_number = int("".join(w.text for w in value_words))
        return account_number

    def get_issued_date(self, words_per_page: Dict[int, List[Word]]) -> dt.date:
        """
        Извлекает с первой страницы выписки дату формирования документа

        :param words_per_page: слова с первой страницы
        :return: дата формирования выписки
        :raise IndexError: дата формирования выписки не найдена
        """
        return self._get_issued_date(words_per_page[0], "Дата выдачи:")

    def get_owner_name(self, words_per_page: Dict[int, List[Word]]) -> str:
        """
        Извлекает с первой страницы выписки имя владельца счёта

        :param words_per_page: слова с первой страницы
        :return: имя владельца счёта
        :raise IndexError: имя владельца счёта не найдена
        """
        current_words = words_per_page[0]

        try:
            label_start_i, label_end_i = self._look_up_collocation("Клиент", current_words)
        except IndexError as e:
            raise IndexError("no owner name found on first page") from e

        label = current_words[label_start_i]
        current_words = current_words[label_end_i:]

        name_start_i = next(i for i, word in enumerate(current_words) if word.x0 == label.x0)
        name_words = self._get_related_words_in_line(current_words[name_start_i:])
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
        return self._get_period(words_per_page[0], "Период:", shift=1)

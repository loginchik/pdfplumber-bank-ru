from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime as dt
from pathlib import Path
import re
from typing import Tuple, Dict, List

import pdfplumber
from pdfplumber.pdf import PDF

from commons.base import BasicProcessor
from commons.enums import BankNameEnum
from commons.schemas import Word


@dataclass(frozen=True)
class Metadata:
    """
    Структура информации, извлекаемой с первой страницы банковской выписки
    """

    owner_name: str
    account_number: int
    bank_name: BankNameEnum
    issued_date: dt.date
    period: Tuple[dt.date, dt.date]


class BaseMetadataExtractor(ABC, BasicProcessor):
    """
    Базовый класс для обработчика метаданных выписки

    Основной вызываемый метод - ``extract_from_file`` - позволяет открыть PDF-документ
    по заданному файлу и с помощью метода ``extract_from_pdf`` извлечь из него информацию
    о банковской выписке. Также определяет абстрактные методы для обработчиков выписок
    из конкретных банков
    """

    BANK_NAME: BankNameEnum = None

    def extract_from_file(self, filepath: Path) -> Metadata:
        """
        Открывает PDF-файл по заданному пути и извлекает из него метаданные выписки с первой страницы

        :param filepath: путь к PDF-файлу
        :return: метаданные банковской выписки
        """
        self.validate_pdf_file(filepath)
        with pdfplumber.open(filepath) as pdf:
            return self.extract_from_pdf(pdf)

    def extract_from_pdf(self, pdf: PDF) -> Metadata:
        """
        Извлекает метаданные выписки с первой страницы PDF-файла

        :param pdf: PDF
        :return: метаданные выписки
        """
        words_per_page = {page_num: self.get_words(page) for page_num, page in enumerate(pdf.pages[:1])}

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

    def _get_account_number(self, words: List[Word], collocation: str, shift: int = 0) -> int:
        """
        Извлекает с первой страницы выписки номер счёта

        :param words: слова с первой страницы
        :param collocation: искомое словосочетание
        :return: номер счёта
        :raise IndexError: номер счёта не найден
        """
        try:
            account_number = self.__get_word_by_collocation(words, collocation, shift)
        except IndexError as e:
            raise IndexError("no account number found on first page") from e
        account_number = int(re.sub(r"[^0-9]", "", account_number.text))
        return account_number

    def _get_issued_date(self, words: List[Word], collocation: str, shift: int = 0) -> dt.date:
        """
        Извлекает с первой страницы выписки дату формирования документа

        :param words: слова с первой страницы
        :param collocation: искомое словосочетание
        :param shift: сдвиг от искомого словосочетания до даты
        :return: дата формирования выписки
        :raise IndexError: дата формирования выписки не найдена
        """
        try:
            issued_date = self.__get_word_by_collocation(words, collocation, shift)
        except IndexError as e:
            raise IndexError("no issued date found on first page") from e
        return dt.datetime.strptime(issued_date.text, "%d.%m.%Y").date()

    def _get_period(self, words: List[Word], collocation: str, step: int = 2, shift: int = 0) -> Tuple[dt.date, dt.date]:
        """
        Извлекает с первой страницы выписки промежуток дат,
        транзакции за который включены в документ

        :param words: слова с первой страницы
        :param collocation: словосочетание для поиска промежутка дат
        :param step: промежуток в словах между датами
        :param shift: сдвиг до дат от искомого словосочетания
        :return: период выписки
        :raise IndexError: даты периода выписки не найдены
        """
        try:
            _, collocation_end_i = self._look_up_collocation(collocation, words)
        except IndexError as e:
            raise IndexError("no period found on first page") from e

        start_date = words[collocation_end_i + shift]
        end_date = words[collocation_end_i + step + shift]

        start_date = dt.datetime.strptime(start_date.text, "%d.%m.%Y").date()
        end_date = dt.datetime.strptime(end_date.text, "%d.%m.%Y").date()
        return start_date, end_date

    def __get_word_by_collocation(self, words: List[Word], collocation: str, shift: int = 0) -> Word:
        """
        Находит слово по словосочетанию со сдвигом от конца словосочетания

        :param words: слова для поиска
        :param collocation: искомое словосочетание
        :param shift: сдвиг от конца словосочетания
        :return: полученное слово
        :raise IndexError: словосочетание не найдено
        """
        _, prev_text_end_i = self._look_up_collocation(collocation, words)
        return words[prev_text_end_i + shift]

    @staticmethod
    def _get_related_words_in_line(words: List[Word], x_tolerance: int = 3) -> List[Word]:
        """
        Последовательно наполняет список слов, пока они выстроены в одну строку и расположены рядом

        :param words: исходные слова
        :param x_tolerance: макс. расстояние между словами
        :return: собранные слова
        """
        name_words = [words[0]]

        for word in words[1:]:
            if word.top == name_words[0].top and word.x0 - name_words[-1].x1 <= x_tolerance:
                name_words.append(word)
            else:
                break

        return name_words

    @staticmethod
    def _look_up_collocation(collocation: str, words: List[Word]) -> Tuple[int, int]:
        """
        Последовательно перебирает набор слов до тех пор, пока не найдёт заданное словосочетание

        :param collocation: целевое словосочетание
        :param words: слова для перебора
        :return: индексы слов, ограничивающих словосочетание, в исходном наборе
        """
        collocation_words = collocation.split(" ")

        for i, word in enumerate(words):
            if word.text == collocation_words[0]:
                possible_collocation = " ".join([w.text for w in words[i : i + len(collocation_words)]])
                if possible_collocation == collocation:
                    return i, i + len(collocation_words)

        raise IndexError(f"collocation '{collocation}' no found in words")

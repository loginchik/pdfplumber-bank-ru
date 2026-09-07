# pdfplumber-bank-ru

``pdfplumber-bank-ru`` — библиотека для конвертации PDF-файлов банковских выписок о движении средств в ``pandas.DataFrame`` для последующей обработки и аналитики

Поддерживаются выписки Альфа-банк, Ozon Банк, Райффайзенбанк, ТБанк, Яндекс Банк. Протестировано на Python 3.11, 3.12, 3.13, 3.14. 

## Установка

```bash
pip install git+https://github.com/loginchik/pdfplumber-bank-ru
```

## Использование

Преобразование таблицы в ``pandas.DataFrame``: 

```python
from pathlib import Path

from pdfplumber_bank_ru.table import TBankTableExtractor


df = TBankTableExtractor().extract_from_file(filepath=Path("foo/path-to-pdf.pdf"))
```

Извлечение данных о банковской выписке: 

```python
from pathlib import Path 

from pdfplumber_bank_ru.metadata import TBankMetadataExtractor


meta_data = TBankMetadataExtractor().extract_from_file(filepath=Path("foo/path-to-pdf.pdf"))

print("Owner:", meta_data.owner_name)
print("Bank:", meta_data.bank_name)
print("Issued:", meta_data.issued_date)
print("Account:", meta_data.account_number)
print("Period:", meta_data.period)
```

## Лицензия

[MIT](LICENSE)
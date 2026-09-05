from enum import Enum


class BankNameEnum(str, Enum):
    """
    Названия банков
    """

    ALFA = "Альфа-Банк"
    OZON = "Ozon Банк"
    RAIF = "Райффайзенбанк"
    TBANK = "Т-Банк"


class TableColumnEnum(Enum):
    """
    Колонки в итоговом фрейме с банковскими выписками
    """

    date = "date"
    date_performed = "date_performed"
    document_number = "document_number"
    order_number = "order_number"
    details = "details"
    money_acc_curr = "money_amount_account_currency"
    money_op_curr = "money_amount_operation_currency"
    currency = "currency"
    card_number = "card_number"
    page_no = "page"
    bank_name = "bank_name"
    to_account = "to_account"
    from_account = "from_account"

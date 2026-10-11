from enum import Enum


class PaymentMethod(str, Enum):
    card = "card"
    sbp = "sbp"
    installment = "installment"

class PaymentStatus(str, Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"
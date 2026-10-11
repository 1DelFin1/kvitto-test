from app.models.enums import PaymentStatus


class TariffNotFoundError(Exception):
    def __init__(self, tariff_id: str):
        self.tariff_id = tariff_id


class PromoNotFoundError(Exception):
    def __init__(self, code: str):
        self.code = code


class InvalidTransitionError(Exception):
    def __init__(self, current: PaymentStatus, requested: PaymentStatus):
        self.current = current
        self.requested = requested
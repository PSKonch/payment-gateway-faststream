from enum import StrEnum


class PaymentStatus(StrEnum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class ProviderStatus(StrEnum):
    CREATED = "Created"
    COMPLETED = "Completed"
    CANCELED = "Canceled"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"

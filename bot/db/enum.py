import enum


class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPPORT = "support"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    SUCCESS = "success"
    REFUNDED = "refunded"


class TransactionType(str, enum.Enum):
    TOPUP = "topup"
    REFERRAL_BONUS = "referral_bonus"
    WITHDRAW_REQUEST = "withdraw_request"

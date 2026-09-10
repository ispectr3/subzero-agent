from dataclasses import dataclass
from typing import Optional


@dataclass
class Category:
    id: Optional[int]
    name: str
    type: str  # 'INCOME' ou 'EXPENSE'
    icon: str = ""

    def __post_init__(self):
        if self.type not in ("INCOME", "EXPENSE"):
            raise ValueError("O tipo da categoria deve ser 'INCOME' ou 'EXPENSE'.")


@dataclass
class Transaction:
    id: Optional[int]
    amount: float
    category_id: int
    description: str
    date: str  # YYYY-MM-DD
    category_name: Optional[str] = None
    category_type: Optional[str] = None
    category_icon: Optional[str] = None
    created_at: Optional[str] = None

    def is_income(self) -> bool:
        return self.category_type == "INCOME"

    def is_expense(self) -> bool:
        return self.category_type == "EXPENSE"


@dataclass
class Subscription:
    id: Optional[int]
    name: str
    amount: float
    cadence: str  # 'MONTHLY', 'YEARLY', 'WEEKLY'
    status: str  # 'ACTIVE', 'CANCELLED', 'PAUSED'
    category_name: str
    first_seen: str
    last_seen: str
    charges_count: int = 1
    previous_amount: Optional[float] = None
    price_change_pct: Optional[float] = None
    annual_impact: float = 0.0

    def __post_init__(self):
        if self.cadence == "MONTHLY":
            self.annual_impact = self.amount * 12.0
        elif self.cadence == "YEARLY":
            self.annual_impact = self.amount
        elif self.cadence == "WEEKLY":
            self.annual_impact = self.amount * 52.0
        else:
            self.annual_impact = self.amount * 12.0


@dataclass
class Anomaly:
    id: Optional[int]
    type: str  # 'DUPLICATE_CHARGE', 'PRICE_INCREASE', 'GHOST_SUBSCRIPTION', 'UNUSUAL_AMOUNT'
    severity: str  # 'HIGH', 'MEDIUM', 'INFO'
    merchant: str
    description: str
    amount: float
    date: str
    resolved: bool = False

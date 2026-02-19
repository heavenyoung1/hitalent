from dataclasses import dataclass
from datetime import date


@dataclass
class Department:
    """Подразделение"""

    name: str
    parent_id: int | None
    id: int | None = None


@dataclass
class Employee:
    """Сотрудник"""

    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    id: int | None = None

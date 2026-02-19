from dataclasses import dataclass
from datetime import date


@dataclass
class Department:
    """Подразделение"""

    id: int
    name: str
    parent_id: int | None


@dataclass
class Employee:
    """Сотрудник"""

    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date

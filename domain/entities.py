from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class DepartmentDetails:
    """Подразделение с сотрудниками и вложенным поддеревом"""

    id: int
    name: str
    parent_id: int | None
    employees: list[Employee] = field(default_factory=list)
    children: list[DepartmentDetails] = field(default_factory=list)

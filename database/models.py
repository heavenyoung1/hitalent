from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimeStampMixin


class Department(TimeStampMixin, Base):
    __tablename__ = 'departments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # FK - на саму себя - ключ для саомоссылки
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey('departments.id'), nullable=True
    )

    parent: Mapped[Optional['Department']] = relationship(
        back_populates='children',
        remote_side='Department.id',
    )

    children: Mapped[list['Department']] = relationship(back_populates='parent')

    employees: Mapped[list['Employee']] = relationship(back_populates='department')


class Employee(TimeStampMixin, Base):
    __tablename__ = 'employees'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id'))
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str] = mapped_column(String, nullable=False)
    hired_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    department: Mapped['Department'] = relationship(back_populates='employees')

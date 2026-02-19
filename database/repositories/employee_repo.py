from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from domain.entities import Employee

from ..mappers import EmployeeMapper
from ..models import Employee as EmployeeORM


class EmployeeRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, employee: Employee):
        try:
            # 1. Конвертация доменной сущности в ORM-объект
            orm_employee = EmployeeMapper.to_orm(employee)

            # 2. Добавление в сессию
            self.session.add(orm_employee)

            # 3. flush() — отправляем в БД, получаем ID
            await self.session.flush()

            # 4. Обновляем ID в доменном объекте
            employee.id = orm_employee.id

            logger.info(f'Сотрудник сохранён. ID - {employee.id}')
            return employee

        except SQLAlchemyError as e:
            logger.error(f'Ошибка при сохранении. {e}')
            raise e

    async def delete(self, id: int) -> bool:
        try:
            # 1. Выполнение запроса на извлечение данных из БД
            stmt = select(EmployeeORM).where(EmployeeORM.id == id)
            result = await self.session.execute(stmt)
            orm_employee = result.scalar_one_or_none()

            if not orm_employee:
                logger.warning('Сотрудник не найден')
                raise ValueError('Сотрудник не найден')

            # 2. Удаление
            await self.session.delete(orm_employee)
            await self.session.flush()

            return True

        except SQLAlchemyError as e:
            logger.error(f'Ошибка при удалении. {e}')
            raise e

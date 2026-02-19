from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from domain.entities import Department

from ..mappers import DepartmentMapper
from ..models import Department as DepartmentORM


class DepartmentRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, department: Department):
        try:
            # 1. Конвертация доменной сущности в ORM-объект
            orm_department = DepartmentMapper.to_orm(department)

            # 2. Добавление в сессию
            self.session.add(orm_department)

            # 3. flush() — отправляем в БД, получаем ID
            await self.session.flush()

            # 4. Обновляем ID в доменном объекте
            department.id = orm_department.id

            logger.info(f'Департамент сохранён. ID - {department.id}')
            return department


        except SQLAlchemyError as e:
            logger.error(f'Ошибка при сохранении. {e}')
            raise e


    async def delete(self, id: int) -> bool:
        try:
            # 1. Выполнение запроса на извлечение данных из БД
            stmt = select(DepartmentORM).where(DepartmentORM.id == id)
            result = await self.session.execute(stmt)
            orm_department = result.scalar_one_or_none()

            if not orm_department:
                logger.warning('Департамент не найден')
                raise ValueError('Департамент не найден')

            # 2. Удаление
            await self.session.delete(orm_department)
            await self.session.flush()

            return True

        except SQLAlchemyError as e:
            logger.error(f'Ошибка при удалении. {e}')
            raise e


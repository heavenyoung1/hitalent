from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logger import logger
from domain.entities import Department, DepartmentDetails

from ..mappers import DepartmentMapper, EmployeeMapper
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

    async def update(self, upd_department: Department) -> 'Department':
        try:
            # 1. Выполнение запроса на извлечение данных из БД
            stmt = select(DepartmentORM).where(DepartmentORM.id == upd_department.id)
            result = await self.session.execute(stmt)
            orm_department = result.scalars().first()

            # 2. Проверка наличия записи в БД
            if not orm_department:
                logger.error(f' с ID {upd_department.id} не найдено.')
                return None

            # 3. Обновление полей ORM-объекта из доменной сущности
            orm_upd_department = DepartmentMapper.to_orm(upd_department)

            # 4. Сохранение в БД
            await self.session.flush()

            # 5. Возврат доменного объекта
            logger.info(f'Департамент обновлен. ID = {orm_upd_department.id}')
            return DepartmentMapper.to_domain(orm_upd_department)

        except SQLAlchemyError as e:
            logger.error(f'Ошибка БД при обновлении департамента ID = {upd_department.id}: {e}')
            raise e

    async def get(self, id: int):
        try:
            # 1. Получение записи из базы данных
            stmt = select(DepartmentORM).where(DepartmentORM.id == id)
            result = await self.session.execute(stmt)
            orm_department = result.scalars().first()

            # 2. Проверка существования записи в БД
            if not orm_department:
                return None
                # raise EntityNotFoundException(f'Дело с ID {id} не найдено')

            # 3. Преобразование ORM объекта в доменную сущность
            department = DepartmentMapper.to_domain(orm_department)

            logger.info(f'Департмент получен. ID - {department.id}')
            return department

        except SQLAlchemyError as e:
            logger.error(f'Ошибка БД при получении дела ID = {id}: {e}')
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

    async def get_with_details(
        self,
        id: int,
        depth: int = 1,
        include_employees: bool = True,
    ) -> DepartmentDetails | None:
        depth = min(max(depth, 0), 5)  # clamp: 0..5

        try:
            # 1. Загружаем корневое подразделение (+ сотрудников, если нужно)
            stmt = select(DepartmentORM).where(DepartmentORM.id == id)
            if include_employees:
                stmt = stmt.options(selectinload(DepartmentORM.employees))

            result = await self.session.execute(stmt)
            orm_dept = result.scalars().first()

            if not orm_dept:
                logger.warning(f'Подразделение ID={id} не найдено')
                return None

            # 2. Рекурсивно строим дерево, начиная с уровня 0
            details = await self._build_tree(orm_dept, depth, include_employees, current_level=0)

            logger.info(f'Подразделение ID={id} получено (depth={depth}, employees={include_employees})')
            return details

        except SQLAlchemyError as e:
            logger.error(f'Ошибка БД при получении деталей подразделения ID={id}: {e}')
            raise e

    async def _build_tree(
        self,
        orm_dept: DepartmentORM,
        max_depth: int,
        include_employees: bool,
        current_level: int,
    ) -> DepartmentDetails:
        # Конвертируем сотрудников текущего подразделения
        employees = []
        if include_employees:
            sorted_emps = sorted(orm_dept.employees, key=lambda e: e.created_at)
            employees = [EmployeeMapper.to_domain(e) for e in sorted_emps]

        # Загружаем дочерние подразделения, если ещё не достигли максимальной глубины
        children = []
        if current_level < max_depth:
            stmt = select(DepartmentORM).where(DepartmentORM.parent_id == orm_dept.id)
            if include_employees:
                stmt = stmt.options(selectinload(DepartmentORM.employees))

            result = await self.session.execute(stmt)
            child_orms = result.scalars().all()

            for child_orm in child_orms:
                child_details = await self._build_tree(
                    child_orm, max_depth, include_employees, current_level + 1
                )
                children.append(child_details)

        return DepartmentDetails(
            id=orm_dept.id,
            name=orm_dept.name,
            parent_id=orm_dept.parent_id,
            employees=employees,
            children=children,
        )


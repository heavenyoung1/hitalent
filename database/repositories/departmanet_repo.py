from sqlalchemy import delete as sql_delete, select, update as sql_update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logger import logger
from domain.entities import Department, DepartmentDetails

from ..mappers import DepartmentMapper, EmployeeMapper
from ..models import Department as DepartmentORM
from ..models import Employee as EmployeeORM


class DepartmentRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, department: Department) -> Department:
        try:
            orm_department = DepartmentMapper.to_orm(department)
            self.session.add(orm_department)
            await self.session.flush()
            department.id = orm_department.id
            logger.info(f'Департамент сохранён. ID={department.id}')
            return department
        except SQLAlchemyError as e:
            logger.error(f'Ошибка при сохранении департамента: {e}')
            raise

    async def update(self, upd_department: Department) -> Department | None:
        try:
            stmt = select(DepartmentORM).where(DepartmentORM.id == upd_department.id)
            result = await self.session.execute(stmt)
            orm_department = result.scalars().first()

            if not orm_department:
                logger.error(f'Департамент с ID={upd_department.id} не найден.')
                return None

            orm_department.name = upd_department.name
            orm_department.parent_id = upd_department.parent_id
            await self.session.flush()

            logger.info(f'Департамент обновлён. ID={orm_department.id}')
            return DepartmentMapper.to_domain(orm_department)

        except SQLAlchemyError as e:
            logger.error(f'Ошибка БД при обновлении департамента ID={upd_department.id}: {e}')
            raise

    async def get(self, id: int) -> Department | None:
        try:
            stmt = select(DepartmentORM).where(DepartmentORM.id == id)
            result = await self.session.execute(stmt)
            orm_department = result.scalars().first()

            if not orm_department:
                return None

            department = DepartmentMapper.to_domain(orm_department)
            logger.info(f'Департамент получен. ID={department.id}')
            return department

        except SQLAlchemyError as e:
            logger.error(f'Ошибка БД при получении департамента ID={id}: {e}')
            raise

    async def delete(self, id: int) -> bool:
        try:
            stmt = select(DepartmentORM).where(DepartmentORM.id == id)
            result = await self.session.execute(stmt)
            orm_department = result.scalar_one_or_none()

            if not orm_department:
                logger.warning(f'Департамент ID={id} не найден при удалении')
                raise ValueError('Департамент не найден')

            await self.session.delete(orm_department)
            await self.session.flush()
            return True

        except SQLAlchemyError as e:
            logger.error(f'Ошибка при удалении департамента ID={id}: {e}')
            raise

    async def name_exists_in_parent(
        self,
        name: str,
        parent_id: int | None,
        exclude_id: int | None = None,
    ) -> bool:
        """Проверяет уникальность имени в пределах одного parent."""
        stmt = select(DepartmentORM.id).where(
            DepartmentORM.name == name,
            DepartmentORM.parent_id == parent_id,
        )
        if exclude_id is not None:
            stmt = stmt.where(DepartmentORM.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _collect_subtree_ids(self, root_id: int) -> list[int]:
        """BFS-обход поддерева, возвращает все ID (корень первым)."""
        ids: list[int] = []
        queue = [root_id]
        while queue:
            current_id = queue.pop(0)
            ids.append(current_id)
            result = await self.session.execute(
                select(DepartmentORM.id).where(DepartmentORM.parent_id == current_id)
            )
            queue.extend(result.scalars().all())
        return ids

    async def is_descendant(self, ancestor_id: int, potential_descendant_id: int) -> bool:
        """Проверяет, находится ли potential_descendant_id в поддереве ancestor_id."""
        all_ids = await self._collect_subtree_ids(ancestor_id)
        return potential_descendant_id in all_ids

    async def cascade_delete(self, id: int) -> None:
        """Удаляет подразделение, всех сотрудников и все дочерние подразделения."""
        try:
            all_ids = await self._collect_subtree_ids(id)

            # Удаляем всех сотрудников из всего поддерева
            await self.session.execute(
                sql_delete(EmployeeORM).where(EmployeeORM.department_id.in_(all_ids))
            )

            # Удаляем подразделения от листьев к корню (reversed BFS)
            for dept_id in reversed(all_ids):
                result = await self.session.execute(
                    select(DepartmentORM).where(DepartmentORM.id == dept_id)
                )
                orm_dept = result.scalar_one_or_none()
                if orm_dept:
                    await self.session.delete(orm_dept)

            await self.session.flush()
            logger.info(f'Каскадное удаление поддерева ID={id} завершено ({len(all_ids)} подразделений)')

        except SQLAlchemyError as e:
            logger.error(f'Ошибка при каскадном удалении департамента ID={id}: {e}')
            raise

    async def reassign_and_delete(self, id: int, reassign_to_id: int) -> None:
        """Переводит сотрудников в reassign_to_id, дочерние подразделения — к parent,
        затем удаляет подразделение."""
        try:
            dept = await self.get(id)
            if dept is None:
                raise ValueError(f'Департамент ID={id} не найден')

            # Переводим сотрудников
            await self.session.execute(
                sql_update(EmployeeORM)
                .where(EmployeeORM.department_id == id)
                .values(department_id=reassign_to_id)
            )

            # Дочерние подразделения переходят к parent текущего
            await self.session.execute(
                sql_update(DepartmentORM)
                .where(DepartmentORM.parent_id == id)
                .values(parent_id=dept.parent_id)
            )

            # Удаляем само подразделение
            result = await self.session.execute(
                select(DepartmentORM).where(DepartmentORM.id == id)
            )
            orm_dept = result.scalar_one_or_none()
            if orm_dept:
                await self.session.delete(orm_dept)

            await self.session.flush()
            logger.info(f'Подразделение ID={id} удалено, сотрудники переведены в ID={reassign_to_id}')

        except SQLAlchemyError as e:
            logger.error(f'Ошибка при reassign-удалении департамента ID={id}: {e}')
            raise

    async def get_with_details(
        self,
        id: int,
        depth: int = 1,
        include_employees: bool = True,
    ) -> DepartmentDetails | None:
        depth = min(max(depth, 0), 5)

        try:
            stmt = select(DepartmentORM).where(DepartmentORM.id == id)
            if include_employees:
                stmt = stmt.options(selectinload(DepartmentORM.employees))

            result = await self.session.execute(stmt)
            orm_dept = result.scalars().first()

            if not orm_dept:
                logger.warning(f'Подразделение ID={id} не найдено')
                return None

            details = await self._build_tree(orm_dept, depth, include_employees, current_level=0)
            logger.info(f'Подразделение ID={id} получено (depth={depth}, employees={include_employees})')
            return details

        except SQLAlchemyError as e:
            logger.error(f'Ошибка БД при получении деталей подразделения ID={id}: {e}')
            raise

    async def _build_tree(
        self,
        orm_dept: DepartmentORM,
        max_depth: int,
        include_employees: bool,
        current_level: int,
    ) -> DepartmentDetails:
        employees = []
        if include_employees:
            sorted_emps = sorted(orm_dept.employees, key=lambda e: e.created_at)
            employees = [EmployeeMapper.to_domain(e) for e in sorted_emps]

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

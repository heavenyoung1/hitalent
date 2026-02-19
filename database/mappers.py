import database.models as orm
import domain.entities as domain


class DepartmentMapper:
    @staticmethod
    def to_domain(model: orm.Department) -> domain.Department:
        return domain.Department(
            id=model.id,
            name=model.name,
            parent_id=model.parent_id,
        )

    @staticmethod
    def to_orm(entity: domain.Department) -> orm.Department:
        return orm.Department(
            name=entity.name,
            parent_id=entity.parent_id,
        )


class EmployeeMapper:
    @staticmethod
    def to_domain(model: orm.Employee) -> domain.Employee:
        return domain.Employee(
            id=model.id,
            department_id=model.department_id,
            full_name=model.full_name,
            position=model.position,
            hired_at=model.hired_at,
        )

    @staticmethod
    def to_orm(entity: domain.Employee) -> orm.Employee:
        return orm.Employee(
            department_id=entity.department_id,
            full_name=entity.full_name,
            position=entity.position,
            hired_at=entity.hired_at,
        )

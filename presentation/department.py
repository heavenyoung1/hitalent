from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import database
from database.repositories.departmanet_repo import DepartmentRepo
from database.repositories.employee_repo import EmployeeRepo
from domain.entities import Department, Employee

from .dto import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
    DepartmentResponse,
    DepartmentDetailsResponse,
    EmployeeCreateRequest,
    EmployeeResponse,
)

# ========== ROUTER ==========
router = APIRouter(prefix='/api/v0', tags=['department'])


# ========== DEPENDENCIES ==========
async def get_session():
    async with database.get_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ========== ENDPOINTS ==========

@router.post(
    '/departments',
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создание нового подразделения',
)
async def create_department(
    request: DepartmentCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> DepartmentResponse:
    repo = DepartmentRepo(session)

    if request.parent_id is not None:
        parent = await repo.get(request.parent_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Родительское подразделение не найдено',
            )

    if await repo.name_exists_in_parent(request.name, request.parent_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Подразделение с таким именем уже существует в данном родителе',
        )

    department = Department(name=request.name, parent_id=request.parent_id)

    try:
        saved = await repo.save(department)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return DepartmentResponse(id=saved.id, name=saved.name, parent_id=saved.parent_id)


@router.post(
    '/departments/{id}/employees/',
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создание нового сотрудника в подразделении',
)
async def create_employee(
    id: int,
    request: EmployeeCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> EmployeeResponse:
    dept_repo = DepartmentRepo(session)
    dept = await dept_repo.get(id)
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Подразделение не найдено',
        )

    emp_repo = EmployeeRepo(session)
    employee = Employee(
        department_id=id,
        full_name=request.full_name,
        position=request.position,
        hired_at=request.hired_at,
    )

    try:
        saved = await emp_repo.save(employee)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return EmployeeResponse(
        id=saved.id,
        department_id=saved.department_id,
        full_name=saved.full_name,
        position=saved.position,
        hired_at=saved.hired_at,
    )


@router.get(
    '/departments/{id}',
    response_model=DepartmentDetailsResponse,
    status_code=status.HTTP_200_OK,
    summary='Получить подразделение (детали + сотрудники + поддерево)',
)
async def get_department(
    id: int,
    depth: int = Query(default=1, ge=0, le=5, description='Глубина вложенных подразделений (0–5)'),
    include_employees: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
) -> DepartmentDetailsResponse:
    repo = DepartmentRepo(session)
    details = await repo.get_with_details(id, depth=depth, include_employees=include_employees)

    if details is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Подразделение не найдено')

    def to_response(d) -> DepartmentDetailsResponse:
        return DepartmentDetailsResponse(
            id=d.id,
            name=d.name,
            parent_id=d.parent_id,
            employees=[
                EmployeeResponse(
                    id=e.id,
                    department_id=e.department_id,
                    full_name=e.full_name,
                    position=e.position,
                    hired_at=e.hired_at,
                )
                for e in d.employees
            ],
            children=[to_response(c) for c in d.children],
        )

    return to_response(details)


@router.patch(
    '/departments/{id}',
    response_model=DepartmentResponse,
    status_code=status.HTTP_200_OK,
    summary='Переименовать или переместить подразделение',
)
async def update_department(
    id: int,
    request: DepartmentUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> DepartmentResponse:
    repo = DepartmentRepo(session)

    dept = await repo.get(id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Подразделение не найдено')

    new_name = request.name if request.name is not None else dept.name
    new_parent_id = (
        request.parent_id if 'parent_id' in request.model_fields_set else dept.parent_id
    )

    if new_parent_id == id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Подразделение не может быть родителем самого себя',
        )

    if new_parent_id is not None:
        parent = await repo.get(new_parent_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Родительское подразделение не найдено',
            )
        if await repo.is_descendant(ancestor_id=id, potential_descendant_id=new_parent_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Нельзя создать цикл в дереве подразделений',
            )

    if new_name != dept.name or new_parent_id != dept.parent_id:
        if await repo.name_exists_in_parent(new_name, new_parent_id, exclude_id=id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Подразделение с таким именем уже существует в данном родителе',
            )

    dept.name = new_name
    dept.parent_id = new_parent_id

    try:
        updated = await repo.update(dept)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return DepartmentResponse(id=updated.id, name=updated.name, parent_id=updated.parent_id)


@router.delete(
    '/departments/{id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Удаление подразделения (cascade или reassign)',
    responses={
        204: {'description': 'Подразделение успешно удалено'},
        400: {'description': 'Неверные параметры'},
        404: {'description': 'Подразделение не найдено'},
    },
)
async def delete_department(
    id: int,
    mode: str = Query(..., description='cascade — удалить всё поддерево; reassign — перевести сотрудников'),
    reassign_to_department_id: int | None = Query(
        default=None,
        description='ID подразделения для перевода сотрудников (обязателен при mode=reassign)',
    ),
    session: AsyncSession = Depends(get_session),
):
    if mode not in ('cascade', 'reassign'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='mode должен быть "cascade" или "reassign"',
        )

    if mode == 'reassign' and reassign_to_department_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='reassign_to_department_id обязателен при mode=reassign',
        )

    repo = DepartmentRepo(session)

    dept = await repo.get(id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Подразделение не найдено')

    try:
        if mode == 'cascade':
            await repo.cascade_delete(id)
        else:
            if reassign_to_department_id == id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Нельзя переводить сотрудников в удаляемое подразделение',
                )
            target = await repo.get(reassign_to_department_id)
            if target is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Целевое подразделение для reassign не найдено',
                )
            await repo.reassign_and_delete(id, reassign_to_department_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

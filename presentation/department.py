from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import database
from database.repositories.departmanet_repo import DepartmentRepo
from database.repositories.employee_repo import EmployeeRepo 
from domain.entities import Department

from .dto import (
    EmployeeCreateRequest,
    EmployeeResponse,
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentDetailsResponse,
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
    summary='Создание нового департамента',
)
async def create_department(
    request: DepartmentCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> DepartmentResponse:
    repo = DepartmentRepo(session)

    department = Department(
        name=request.name,
        parent_id=request.parent_id,
    )

    try:
        saved = await repo.save(department)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return DepartmentResponse(
        id=saved.id,
        name=saved.name,
        parent_id=saved.parent_id,
    )

@router.post(
    '/departments/{id}/employees/',
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создание нового сотрудника',
)
async def create_department(
    request: EmployeeCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> DepartmentResponse:
    repo = EmployeeRepo(session)

    employee = Department(
        department_id=request.department_id,
        full_name=request.full_name,
        position=request.position,
        hired_at=request.hired_at,
    )

    try:
        saved = await repo.save(employee)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return DepartmentResponse(
        id=saved.id,
        name=saved.name,
        parent_id=saved.parent_id,
    )



@router.get(
    '/departments/{id}',
    response_model=DepartmentDetailsResponse,
    status_code=status.HTTP_200_OK,
    summary='Получить подразделение (детали + сотрудники + поддерево)',
)
async def get_department(
    id: int,
    depth: int = 1,
    include_employees: bool = True,
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


@router.delete(
    '/departments/{id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Удаление департамента',
)

async def delete_case(
    id: int,
    session: AsyncSession = Depends(get_session),
    responses={
        204: {'description': 'Департамент успешно удалено'},
        404: {'description': 'Департамент не найден'},
    },
):
    repo = DepartmentRepo(session)
    repo.delete(id)
    

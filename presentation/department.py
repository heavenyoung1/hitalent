from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import database
from database.repositories.departmanet_repo import DepartmentRepo
from domain.entities import Department

from .dto import DepartmentCreateRequest, DepartmentResponse

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
    '/department',
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

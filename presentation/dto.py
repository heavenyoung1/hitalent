from datetime import date

from pydantic import BaseModel, ConfigDict, Field

# ============ Department ============

class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., max_length=255, description='Название департамента')
    parent_id: int | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'name': '[DOGE] Department of Government Efficiency',
                'parent_id': 1,
            }
        }
    )

class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: int | None

    model_config = ConfigDict(from_attributes=True)

# ============ Employee ============
class EmployeeCreateRequest(BaseModel):
    department_id: int = Field(...)
    full_name: str = Field(..., max_length=255)
    position: str = Field(..., max_length=255)
    hired_at: date | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            'example': {
                'department_id': 1,
                'full_name': 'Elon Musk',
                'position': 'CEO',
                'hired_at': '2025-01-15',
            }
        }
    )

class EmployeeResponse(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None

    model_config = ConfigDict(from_attributes=True)

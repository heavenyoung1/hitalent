from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============ Department ============

class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: int | None = Field(default=None)

    @field_validator('name')
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('name не может быть пустым')
        return v


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: int | None = Field(default=None)

    @field_validator('name')
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('name не может быть пустым')
        return v


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: int | None

    model_config = ConfigDict(from_attributes=True)


class DepartmentDetailsResponse(BaseModel):
    id: int
    name: str
    parent_id: int | None
    employees: list['EmployeeResponse'] = []
    children: list['DepartmentDetailsResponse'] = []

    model_config = ConfigDict(from_attributes=True)


DepartmentDetailsResponse.model_rebuild()


# ============ Employee ============

class EmployeeCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    position: str = Field(..., min_length=1, max_length=200)
    hired_at: date | None = Field(default=None)

    @field_validator('full_name', 'position')
    @classmethod
    def strip_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Поле не может быть пустым')
        return v


class EmployeeResponse(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None

    model_config = ConfigDict(from_attributes=True)

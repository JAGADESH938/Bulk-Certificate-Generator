import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.validation import NAME_MAX_LENGTH, normalize_string


class RecipientInput(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=NAME_MAX_LENGTH,
        description="Full name of the certificate recipient",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address of the certificate recipient",
        examples=["john.doe@example.com"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return normalize_string(v)

    @field_validator("email")
    @classmethod
    def normalize_email_address(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class CertificateResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    recipient_name: str
    recipient_email: str
    certificate_title: str
    certificate_date: date
    certificate_id: str
    status: str
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedCertificatesResponse(BaseModel):
    items: list[CertificateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

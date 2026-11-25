from pydantic import EmailStr, Field, SecretStr, field_validator

from app.schemas.common import Schema


class RegisterRequest(Schema):
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class TokenRead(Schema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl


class ProviderBase(BaseModel):
    name: str
    website: HttpUrl | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(BaseModel):
    name: str | None = None
    website: HttpUrl | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None


class ProviderOut(ProviderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    proxy_count: int = 0

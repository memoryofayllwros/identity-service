from pydantic import BaseModel, Field


class MobileInfo(BaseModel):
    country_code: str = Field(min_length=1, max_length=8)
    phone_number: str = Field(min_length=1, max_length=32)

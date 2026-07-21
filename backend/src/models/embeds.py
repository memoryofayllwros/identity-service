from pydantic import BaseModel


class MobileInfo(BaseModel):
    country_code: str
    phone_number: str

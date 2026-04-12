from pydantic.main import BaseModel


class StatusUpdateRequest(BaseModel):
    status: str

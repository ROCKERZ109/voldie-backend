from pydantic.main import BaseModel


class MoodRequest(BaseModel):
    mood: str

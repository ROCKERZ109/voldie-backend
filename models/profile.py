from pydantic import BaseModel


class ProfileSchema(BaseModel):
    currentRole: str
    experience: str
    industry: str
    goal: str

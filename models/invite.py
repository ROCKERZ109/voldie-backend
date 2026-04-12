from pydantic import BaseModel
class InviteRequest(BaseModel):
    cafe_name: str
    mood: str

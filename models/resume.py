from typing import List, Optional

from pydantic import BaseModel, Field


class ResumeURLRequest(BaseModel):
    url: str

class ParsedResume(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    raw_text: str = Field(..., description="Full text extracted from CV")
    parsed_skills: List[str] = Field(default_factory=list) # Default is empty list []
    experience_years: int = Field(default=0)
    current_role: Optional[str] = Field(default=None)
    target_roles: List[str] = Field(default_factory=list)
    cv_url: Optional[str] = Field(default=None)

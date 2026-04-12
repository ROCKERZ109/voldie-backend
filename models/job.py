from typing import Optional

from groq import BaseModel


class JobSearchRequest(BaseModel):
    mood: str
    query_type: str = "backend" # Default is backend, but she can change it
    custom_query: Optional[str] = None


class FeedbackRequest(BaseModel):
    user_id: str  # Future use for personalized learning
    action: str  # 'like' or 'dislike'
    job_url: str
    reason: Optional[str] = None

class ExtractRequest(BaseModel):
    url: Optional[str] = None
    raw_text: Optional[str] = None  # Naya field add kiya

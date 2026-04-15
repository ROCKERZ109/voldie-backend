from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import Request

# Import our services
from models.tracker import StatusUpdateRequest
from services.db_service import (
    get_tracked_jobs,
    log_agent_memory,
    save_tracked_job,
    update_job_status,
    delete_job_from_tracker,
)
from models.invite import InviteRequest
from models.job import ExtractRequest, FeedbackRequest, JobSearchRequest
from models.mood import MoodRequest
from services.cafe_service import get_mood_lifting_cafe
from services.vibe_agent import get_vibe_and_quote
from services.job_agent import (
    run_job_hunt,
    extract_job_from_url_or_text,
)  # save_feedback # Hum ye bhi next likhenge
from utils.notifier import send_telegram_alert
from services.resume_agent import router as resume_router

app = FastAPI(title="The Birthday API")

app.include_router(resume_router, prefix="/api/resume", tags=["resume"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production mein isko apne Vercel URL se replace kar dena
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---


@app.get("/")
def health_check():
    return {"status": "120B Architect is awake and plotting destiny."}


@app.post("/api/vibe")
async def get_vibe(request: MoodRequest):
    # Dummy response for now, we will hook up Groq here next

    vibe_response = get_vibe_and_quote(
        request.mood
    )  # Replace with request.mood when ready
    return vibe_response


@app.get("/api/cafe")
async def get_cafe():
    # Directly fetches from Supabase (or fallback)
    cafe = get_mood_lifting_cafe()
    return {"cafe": cafe}


@app.post("/api/invite")
async def send_invite(request: InviteRequest):
    # print(f"🛠️ [DEV MOCK] Code Red Alert triggered for: {request.cafe_name}")
    # success = True # Forcing success for UI testing

    # if success:
    #     return {"message": "Upendra has been notified. He is probably running to the door now."}

    # raise HTTPException(status_code=500, detail="Failed to notify Upendra. The universe glitched.")
    #     # Triggers the Telegram ping
    success = send_telegram_alert(request.cafe_name, request.mood)
    if success:
        return {
            "message": "Upendra has been notified. He is probably running to the door now."
        }
    raise HTTPException(
        status_code=500, detail="Failed to notify Upendra. The universe glitched."
    )


@app.post("/api/jobs")
async def find_jobs(request: JobSearchRequest):
    result = run_job_hunt(request.mood, request.query_type, request.custom_query)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.post("/api/feedback")
async def handle_job_feedback(request: FeedbackRequest):
    """
    Receives Thumbs Up/Down from the frontend.
    """
    success = log_agent_memory(
        user_id=request.user_id,
        action=request.action,
        job_url=request.job_url,
        reason=request.reason,
    )
    if success:
        return {"status": "success", "message": f"Logged {request.action}"}
    return {"status": "error", "message": "Failed to log memory"}


@app.post("/api/extract")
async def extract_metadata(request: ExtractRequest):
    """
    Receives a URL and returns clean JSON metadata for the Tracker.
    """
    data = await extract_job_from_url_or_text(request.url, request.raw_text)
    return {"success": True, "data": data}


@app.post("/api/tracker/save")
async def save_job_to_tracker(request: Request):
    """
    Receives extracted JSON and saves it to DB.
    """
    job_data = await request.json()
    saved_data = save_tracked_job(job_data)

    if saved_data:
        return {
            "success": True,
            "message": "Saved to Command Center!",
            "data": saved_data,
        }
    raise HTTPException(status_code=500, detail="Failed to save to database")


@app.get("/api/tracker")
async def fetch_tracker_jobs():
    jobs = get_tracked_jobs()
    return {"success": True, "data": jobs}


@app.patch("/api/tracker/{job_id}")
async def change_job_status(job_id: str, request: StatusUpdateRequest):
    updated = update_job_status(job_id, request.status)
    if updated:
        return {"success": True, "data": updated}
    raise HTTPException(status_code=500, detail="Failed to update job status")


@app.delete("/api/tracker/{job_id}")
async def delete_job(job_id: str):
    try:
        # Supabase se job delete maar do
        delete_job_from_tracker(job_id)
        return {"status": "success", "message": "Job sent to the void! 🕳️"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

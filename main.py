from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import Request, Depends

# Import our services
from models.profile import ProfileSchema
from services.auth import get_current_user
from models.tracker import StatusUpdateRequest
from services.db_service import (
    create_or_update_user_profile,
    get_tracked_jobs,
    get_user_profile_info,
    log_agent_memory,
    save_tracked_job,
    update_job_status,
    delete_job_from_tracker,
)
from models.job import ExtractRequest, FeedbackRequest, JobSearchRequest
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


@app.post("/api/jobs", tags=["jobs"])
async def find_jobs(request: JobSearchRequest, user_id: str = Depends(get_current_user)):
    result = run_job_hunt(user_id, request.mood, request.custom_query)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.post("/api/feedback", tags=["feedback"])
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


@app.post("/api/extract", tags=["extract"])
async def extract_metadata(request: ExtractRequest):
    """
    Receives a URL and returns clean JSON metadata for the Tracker.
    """
    data = await extract_job_from_url_or_text(request.url, request.raw_text)
    return {"success": True, "data": data}


@app.post("/api/tracker/save", tags=["tracker"])
async def save_job_to_tracker(request: Request, user_id: str = Depends(get_current_user)):
    """
    Receives extracted JSON and saves it to DB.
    """
    job_data = await request.json()
    saved_data = save_tracked_job(job_data, user_id)

    if saved_data:
        return {
            "success": True,
            "message": "Saved to Command Center!",
            "data": saved_data,
        }
    raise HTTPException(status_code=500, detail="Failed to save to database")


@app.get("/api/tracker", tags=["tracker"])
async def fetch_tracker_jobs(user_id: str = Depends(get_current_user)):

    jobs = get_tracked_jobs(user_id)
    return {"success": True, "data": jobs}


@app.patch("/api/tracker/{job_id}", tags=["tracker"])
async def change_job_status(job_id: str, request: StatusUpdateRequest, user_id: str = Depends(get_current_user)):
    updated = update_job_status(job_id, request.status, user_id)
    if updated:
        return {"success": True, "data": updated}
    raise HTTPException(status_code=500, detail="Failed to update job status")


@app.delete("/api/tracker/{job_id}", tags=["tracker"])
async def delete_job(job_id: str, user_id: str = Depends(get_current_user)):
    try:
        # Supabase se job delete maar do
        delete_job_from_tracker(job_id, user_id)
        return {"status": "success", "message": "Job sent to the void! 🕳️"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile", tags=["profile"])
def update_user_profile(profile: ProfileSchema, user_id: str = Depends(get_current_user)):

    # 1. Logic ko service function ke pass bhejo
    result = create_or_update_user_profile(
        user_id=user_id,
        profile_data=profile
    )

    # 2. Result check karo
    if not result["success"]:
        # Agar kuch phata, toh client ko 500 error do
        raise HTTPException(status_code=500, detail=result["error"])

    # 3. Sab theek raha toh success message bhejo
    return {
        "status": "success",
        "message": result["message"]
    }


@app.get("/api/profile/me", tags=["profile"])
def get_user_profile(user_id: str = Depends(get_current_user)):
    try:
        # Supabase se user_id ke base pe profile uthao
        response = get_user_profile_info(user_id)

        # Agar data nahi hai (new user), toh empty object ya null bhej do
        if not response:
            return {"status": "success", "data": None}

        return {"status": "success", "data": response}

    except Exception as e:
        # Agar Supabase error de (like row not found), toh handle karo
        return {"status": "error", "message": str(e), "data": None}

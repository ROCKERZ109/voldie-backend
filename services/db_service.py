
from typing import Optional

from utils.database import get_db


def save_tracked_job(job_data: dict, user_id: str = "anastasia"):

    """
    Saves the extracted job into the Tracker (Kanban Board).
    """
    try:
        supabase = get_db()
        # Default status is 'Saved' (Hitlist)
        data = {
            "title": job_data.get("title", "Unknown Role"),
            "company": job_data.get("company", "Unknown Company"),
            "url": job_data.get("url"),
            "tech_stack": job_data.get("tech_stack", []),
            "hiring_manager": job_data.get("hiring_manager"),
            "vibe": job_data.get("vibe", "No vibe extracted"),
            "status": "Saved",
            "user_id": user_id # If you are tracking users, else remove
        }
        response = supabase.table("tracked_jobs").insert(data).execute()
        return response.data
    except Exception as e:
        print(f"🚨 DB Insert Error: {e}")
        return None


def log_agent_memory(user_id: str, action: str, job_url: str, reason: Optional[str] = None):
    """
    Logs user feedback (like/dislike) for a specific job URL.
    """
    try:
        supabase = get_db()
        data = {"user_id": user_id, "action": action, "job_url": job_url, "reason": reason}
        supabase.table("agent_memory").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error logging agent memory: {e}")
        return False


def get_tracked_jobs(user_id: str = "anastasia"):
    """Fetches all jobs saved in the tracker for the user."""
    try:
        supabase = get_db()
        response = supabase.table("tracked_jobs").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"🚨 DB Fetch Error: {e}")
        return []

def update_job_status(job_id: str, new_status: str):
    """Updates the status of a job (e.g., Saved -> Applied)."""
    try:
        supabase = get_db()
        response = supabase.table("tracked_jobs").update({"status": new_status}).eq("id", job_id).execute()
        return response.data
    except Exception as e:
        print(f"🚨 DB Update Error: {e}")
        return None

def delete_job_from_tracker(job_id: str):
    """Deletes a job from the tracker."""
    try:
        supabase = get_db()
        response = supabase.table("tracked_jobs").delete().eq("id", job_id).execute()
        return response.data
    except Exception as e:
        print(f"🚨 DB Delete Error: {e}")
        return None

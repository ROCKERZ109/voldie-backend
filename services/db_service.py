from typing import Optional

from fastapi import Depends

from utils.database import get_db
from services.auth import get_current_user
import logging

# Logging set up kar le taaki error aane pe terminal pe dikh jaye
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_tracked_job(job_data: dict, user_id: str):
    """
    Saves the extracted job into the Tracker (Kanban Board).
    """
    try:
        supabase = get_db()
        # Default status is 'Saved' (Hitlist)
        print(f"Saving job for user {user_id}: {job_data.get('title', 'No Title')}")
        data = {
            "title": job_data.get("title", "Unknown Role"),
            "company": job_data.get("company", "Unknown Company"),
            "url": job_data.get("url"),
            "tech_stack": job_data.get("tech_stack", []),
            "hiring_manager": job_data.get("hiring_manager"),
            "vibe": job_data.get("vibe", "No vibe extracted"),
            "status": "Saved",
            "user_id": user_id,  # If you are tracking users, else remove
        }
        response = supabase.table("tracked_jobs").insert(data).execute()
        return response.data
    except Exception as e:
        print(f" DB Insert Error: {e}")
        return None


def log_agent_memory(
    action: str,
    job_url: str,
    user_id: str,
    reason: Optional[str] = None,
):
    """
    Logs user feedback (like/dislike) for a specific job URL.
    """
    try:
        supabase = get_db()
        data = {
            "user_id": user_id,
            "action": action,
            "job_url": job_url,
            "reason": reason,
        }
        supabase.table("agent_memory").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error logging agent memory: {e}")
        return False


def get_tracked_jobs(user_id: str):
    """Fetches all jobs saved in the tracker for the user."""
    try:
        supabase = get_db()
        response = (
            supabase.table("tracked_jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data
    except Exception as e:
        print(f" DB Fetch Error: {e}")
        return []


def update_job_status(job_id: str, new_status: str, user_id: str):
    """Updates the status of a job (e.g., Saved -> Applied)."""
    try:
        supabase = get_db()
        response = (
            supabase.table("tracked_jobs")
            .update({"status": new_status})
            .eq("id", job_id)
            .eq("user_id", user_id)
            .execute()
        )
        return response.data
    except Exception as e:
        print(f" DB Update Error: {e}")
        return None


def delete_job_from_tracker(job_id: str, user_id: str):
    """Deletes a job from the tracker."""
    try:
        supabase = get_db()
        response = supabase.table("tracked_jobs").delete().eq("id", job_id).eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        print(f" DB Delete Error: {e}")
        return None


def create_or_update_user_profile(user_id: str, profile_data):
    """
    User profile ko Supabase mein insert ya update (upsert) karta hai.
    """
    try:
        supabase_client = get_db()
        # Data dictionary taiyaar karo DB ke format mein
        data = {
            "user_id": user_id,
            "current_role": profile_data.currentRole,
            "experience": profile_data.experience,
            "industry": profile_data.industry,
            "goal": profile_data.goal,
        }

        logger.info(
            f"Database mein profile upsert kar raha hoon user: {user_id} ke liye"
        )

        # Thuk laga ke Upsert maro!
        response = supabase_client.table("user_profiles").upsert(data).execute()

        return {
            "success": True,
            "message": "Profile successfully saved",
            "data": response.data,
        }

    except Exception as e:
        logger.error(f"Profile save karte waqt ERROR phata: {str(e)}")
        # False return karo ya seedha error raise karo, teri marzi
        return {"success": False, "error": str(e)}


def get_user_profile_info(user_id: str):
    """Fetches the user's profile information."""
    try:
        supabase = get_db()
        response = (
            supabase.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        print(f" DB Fetch Error: {e}")
        return None

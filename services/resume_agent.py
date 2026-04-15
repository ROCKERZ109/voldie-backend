from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional

import requests
from utils.database import get_db
import httpx
import os
import json
import io
from PyPDF2 import PdfReader
from groq import Groq
import supabase
import supabase

from models.resume import ParsedResume, ResumeURLRequest

router = APIRouter()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")

async def extract_text_from_url(url: str) -> str:
    """Uses Jina.ai to convert any web CV into clean Markdown."""
    jina_url = f"https://r.jina.ai/{url}"
    # async with httpx.AsyncClient() as http_client:
    #     response = await http_client.get(jina_url)
    #     if response.status_code != 200:
    #         raise HTTPException(
    #             status_code=400, detail="Jina couldn't read this URL. Is it public?"
    #         )
    #     return response.text
    firecrawl_url = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {"url": url, "formats": ["markdown"], "onlyMainContent": True}

    response = requests.post(
        firecrawl_url, headers=headers, json=data, timeout=18
    )
    if response.status_code == 200:
        result = response.json()
        if result.get("success") and "markdown" in result.get("data", {}):
            text = result["data"]["markdown"]
            compressed_text = " ".join(text.split())

            return compressed_text
    return "Failed to extract text from the URL. Please ensure it's a public page and try again."
def parse_with_groq(text: str) -> dict:
    """Sends raw text to Groq Llama-3 and demands a strict JSON output."""

    prompt = f"""
    You are an elite technical recruiter. Read the following resume text and extract the core details.
    You MUST return ONLY a valid JSON object with the following keys:
    - "parsed_skills" (array of strings, e.g. ["Python", "React", "AWS"])
    - "experience_years" (integer, total years of professional experience. 0 if fresher, check for the year they started in the current role or domain, their experience should strictly be related to the current field of work and calculate accordingly. If it's not clear, make an educated guess based on the roles and projects mentioned. The current year is 2026, so if they started in 2024, that's 2 years of experience. If they have a gap year, don't count that.)
    - "current_role" (string, the person's current or most recent job title)
    - "target_roles" (array of strings, 2-3 job titles they are best suited for based on this resume)

    Resume Text:
    {text}
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",  # Using 70B for maximum reasoning accuracy
            response_format={
                "type": "json_object"
            },
            temperature=0.1,  # Low temp for factual extraction, no hallucination
        )

        # Parse the JSON string returned by Groq
        result_json = json.loads(chat_completion.choices[0].message.content)
        return result_json
    except Exception as e:
        print(f"Groq Parsing Error: {e}")
        raise HTTPException(status_code=500, detail="AI failed to parse the resume.")


# --- API ENDPOINTS ---

def get_resume_profile(user_id: str):
    """Fetches the user's current saved profile to display on the dashboard."""
    try:
        supabase = get_db()
        response = supabase.table('resume_profiles').select('*').eq('user_id', 'anastasia').execute()

        if response.data and len(response.data) > 0:
            return {"status": "success", "data": response.data[0]}
        else:
            return {"status": "not_found", "message": "No profile synced yet."}
    except Exception as e:
        print(f"DB Fetch Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch resume profile from database.")

@router.post("/url")
async def parse_resume_url(request: ResumeURLRequest):
    """Endpoint 1: For GitHub Pages, Notion Docs, or public Web CVs"""
    print(f"🕵️‍♂️ Scanning URL: {request.url}")
    supabase = get_db()
    # 1. Scrape Text
    raw_text = await extract_text_from_url(request.url)
    print(f"Extracted {(raw_text)} characters of text from the URL.")
    # 2. Extract JSON with AI
    parsed_data = parse_with_groq(raw_text)


    # 3. Add raw text to the payload (we might need it later)
    parsed_data["raw_text"] = raw_text
    profile_payload = ParsedResume(
        user_id="anastasia",
        raw_text=parsed_data["raw_text"],
        parsed_skills=parsed_data.get("parsed_skills", []),
        experience_years=parsed_data.get("experience_years", 0),
        current_role=parsed_data.get("current_role", ""),
        target_roles=parsed_data.get("target_roles", []),
        cv_url=request.url,
    )
    supabase.table("resume_profiles").upsert(profile_payload.model_dump(), on_conflict="user_id").execute()

    return {"status": "success", "data": parsed_data}


@router.post("/upload")
async def parse_resume_pdf(file: UploadFile = File(...)):
    """Endpoint 2: For traditional PDF uploads"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed, Bawa!")

    print(f"📄 Processing PDF: {file.filename}")

    try:
        # 1. Read PDF from memory (No need to save to disk!)
        contents = await file.read()
        pdf_reader = PdfReader(io.BytesIO(contents))

        raw_text = ""
        for page in pdf_reader.pages:
            raw_text += page.extract_text() + "\n"

        if not raw_text.strip():
            raise HTTPException(
                status_code=400,
                detail="This PDF looks like an image, I can't read text from it.",
            )

        # 2. Extract JSON with AI
        parsed_data = parse_with_groq(raw_text)
        print(f"Extracted Data: {parsed_data}")
        parsed_data["raw_text"] = raw_text
        supabase = get_db()
        profile_payload = ParsedResume(
            user_id="anastasia",
            raw_text=parsed_data["raw_text"],
            parsed_skills=parsed_data.get("parsed_skills", []),
            experience_years=parsed_data.get("experience_years", 0),
            current_role=parsed_data.get("current_role", ""),
            target_roles=parsed_data.get("target_roles", []),
            cv_url=None,
        )
        supabase.table("resume_profiles").upsert(profile_payload.model_dump(), on_conflict="user_id").execute()

        # TODO: Bawa, yahan pe Supabase DB me save karna hai!

        return {"status": "success", "data": parsed_data}

    except Exception as e:
        print(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_my_profile():
    """Fetches the user's current saved profile to display on the dashboard."""
    try:
        response = get_resume_profile("anastasia")
        if response.get("status") == "success" and len(response.get("data", [])) > 0:
            return {"status": "success", "data": json.loads(json.dumps(response["data"], default=str))}
        else:
            return {"status": "not_found", "message": "No profile synced yet."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

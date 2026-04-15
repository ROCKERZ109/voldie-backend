import os
import json
import logging
from typing import Optional
import requests
import httpx
from dotenv import load_dotenv

# API Clients
from tavily import TavilyClient
from groq import Groq
from openai import OpenAI

# Internal Services
from services.resume_agent import get_resume_profile
from services.db_service import save_tracked_job
from utils.database import get_db
from fastapi import HTTPException

# Load Environment Variables
load_dotenv()

# Configure Logger
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/extractor.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Initialize Keys
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 🚨 Alibaba Qwen Key

# Initialize Clients
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)
db = get_db()

# 🚨 Qwen-Plus Client Setup (OpenAI Compatible Mode)
qwen_client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)


def get_user_memory(user_id="anastasia"):
    """Fetches her past likes and dislikes from Supabase"""
    try:
        response = db.table("agent_memory").select("*").eq("user_id", user_id).execute()
        data = response.data

        disliked_urls = [
            item["job_url"]
            for item in data
            if item["action"] == "dislike" and item.get("job_url")
        ]
        liked_reasons = [
            item["reason"]
            for item in data
            if item["action"] == "like" and item.get("reason")
        ]

        memory_str = ""
        if liked_reasons:
            memory_str += (
                f"She previously liked jobs because: {', '.join(liked_reasons)}. "
            )

        if disliked_urls:
            memory_str += f"CRITICAL: She strictly rejected jobs with these URLs. DO NOT include these URLs in your output under any circumstances:\n"
            memory_str += "\n".join([f"- {url}" for url in disliked_urls])

        return (
            memory_str
            if memory_str
            else "No past memory yet. She is an open book today."
        )
    except Exception as e:
        print(f"🚨 Memory Error: {e}")
        return "No memory available."


def generate_dynamic_queries(query_type):
    return [
        f"Junior {query_type} developer jobs Gothenburg entry level 2026",
        f"Junior {query_type} engineer jobs Gothenburg entry level 2026",
        f"Software engineer Gothenburg 'no experience required' {query_type}",
        f"Graduate software program Sweden 2026 {query_type} fullstack",
        f"Entry level software engineer Gothenburg startup jobs",
        f"Entry level software developer Gothenburg startup jobs",
        f"React python node junior jobs Gothenburg 2026",
    ]


def agentic_job_search(query_type="backend", custom_query=None):
    if custom_query and custom_query.strip():
        print(f"Custom Mode Activated! Exact search: '{custom_query}'")
        queries = [custom_query] # Sirf ek exact query jayegi!
    else:
        print("Auto Search Mode Activated! Generating dynamic queries...")
        queries = generate_dynamic_queries(query_type)
    all_results = []
    print(f"Executing Tavily searches for {(queries)} queries...")
    for q in queries:
        search_result = tavily_client.search(
            query=q,
            search_depth="advanced",
            max_results=5,
            include_domains=[
                "linkedin.com",
                "glassdoor.com",
                "indeed.com",
            ],
        )
        all_results.extend(search_result.get("results", []))

    return all_results


def extract_page_content(url, fallback_snippet):
    try:
        # ROUTE 1: THE LINKEDIN HACK (Uses Jina.ai)
        if "linkedin" in url:
            print(f"🔵 LinkedIn detected. Routing to Jina.ai for {url[:30]}...")
            reader_url = f"https://r.jina.ai/{url}"
            response = requests.get(reader_url, timeout=20)

            if response.status_code == 200 and "Just a moment..." not in response.text:
                text = response.text
                if "Sign in to create job alert" in text:
                    text = text.split("Sign in to create job alert")[1]
                elif "Agree & Join LinkedIn" in text:
                    text = text.split("Agree & Join LinkedIn")[1]

                compressed_text = " ".join(text.split())
                print("✅ Jina deep-read successful!")
                return compressed_text
            else:
                return fallback_snippet

        # ROUTE 2: FIRECRAWL FOR THE REST
        else:
            print(f"🔥 Generic site detected. Routing to Firecrawl for {url[:30]}...")
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
                    print("✅ Firecrawl deep-read successful!")
                    return compressed_text
                else:
                    return fallback_snippet
            else:
                return fallback_snippet

    except Exception as e:
        print(f"🚨 Deep-read error: {e}. Using Tavily Fallback!")
        return fallback_snippet


def process_jobs_with_ai(mood, raw_results, memory="", resume_data=None):
    context = ""
    print("🧠 Architect is preparing to analyze the job leads with deep content...")

    for idx, j in enumerate(raw_results[:10]):
        deep_content = extract_page_content(j["url"], fallback_snippet=j["content"])
        if "Clear text" in deep_content:
            parts = deep_content.split("Job type", 1)
            if len(parts) > 1:
                deep_content = parts[1]
        context += f"JOB #{idx}\nTitle: {j['title']}\nURL: {j['url']}\nDeep Content: {deep_content}\n---\n"

    # 🧠 INTELLIGENCE INJECTION: Format the resume for the AI
    resume_context = "No synced resume available. Rely on general Junior/Entry-level matching."
    if resume_data:
        resume_context = f"""
        CANDIDATE PROFILE (FROM SYNCED CV):
        - Current Role: {resume_data.get('current_role', 'Not specified')}
        - Experience: {resume_data.get('experience_years', 0)} years
        - Core Tech Stack: {', '.join(resume_data.get('parsed_skills', []))}
        - Target Roles: {', '.join(resume_data.get('target_roles', []))}
        """

    SYSTEM_PROMPT = f"""
    You are 'The Architect,' an elite, highly analytical AI Tech Recruiter.
    Mission: Filter the provided raw job postings and deep content to find the absolute best software engineering roles for this specific candidate.

    USER MEMORY (Her career preferences):
    {memory}

    {resume_context}

    STRICT FILTERING RULES:
    1. EXPERIENCE CHECK: Cross-reference the job's required experience with the CANDIDATE PROFILE. REJECT immediately if the job demands 'Senior', 'Lead', or significantly more years of experience than she has.
    2. SKILL ALIGNMENT: Prioritize jobs where the required technologies overlap strongly with her Core Tech Stack.
    3. ANTI-AGGREGATOR RULE (CRITICAL): DO NOT output generic search pages or lists. You MUST extract SPECIFIC, individual job roles.
    4. SMART URL EXTRACTION: Extract the specific URL associated with that individual job.

    CRITICAL INSTRUCTION: You MUST output ONLY valid JSON.
    Format required exactly like this:
    {{
        "market_analysis": "A sharp, encouraging 1-2 sentence professional analysis.",
        "jobs": [
            {{
                "title": "Exact Individual Job Title (e.g. Junior Developer)",
                "company": "Specific Company Name",
                "apply_url": "The specific URL for this individual job extracted from the Markdown.",
                "match_reason": "A precise reason why this specific role fits her, EXPLICITLY mentioning her parsed skills (e.g., 'Matches your React and Next.js stack perfectly')."
            }}
        ]
    }}
    """

    print("🧠 Elite 120B Recruiter (Qwen-Plus) is cross-referencing jobs with CV...")
    try:
        completion = qwen_client.chat.completions.create(
            model="qwen3.5-plus",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"You are a supportive career coach. The user is currently feeling '{mood}'. Do NOT discard high-quality jobs that match her profile. Instead, select the best IT jobs from the context and tailor the 'match_reason' to BOTH her CV skills and her mood. \n- If feeling 'burnt out', highlight mentorship or tech she already knows well.\n- If feeling 'pumped', highlight growth or new stack challenges.\nContext:\n{context}\n\nCRITICAL: You must return your final output in JSON format.",
                },
            ],
            temperature=0.3, # Solid sweet spot!
            response_format={"type": "json_object"},
        )
        raw_output = completion.choices[0].message.content
        return json.loads(raw_output)
    except Exception as e:
        print(f"🚨 Qwen LLM Error: {e}")
        return {"error": "The Recruiter AI encountered an error."}


def run_job_hunt(mood: str, query_type="backend", custom_query=None):
    try:
        memory = get_user_memory()
        print(f"🧠 Memory Loaded: {memory}")

        raw_results = agentic_job_search(query_type, custom_query)
        resume_data = get_resume_profile("anastasia")
        if not raw_results:
            return {
                "market_analysis": "The market is unusually quiet today. Let's try adjusting our search parameters later.",
                "jobs": [],
            }

        final_json = process_jobs_with_ai(mood, raw_results, memory, resume_data=resume_data)
        return final_json

    except Exception as e:
        print(f"🚨 Critical Failure in run_job_hunt: {e}")
        return {"error": "Failed to run the job hunt. Please check server logs."}


async def extract_job_from_url_or_text(
    url: Optional[str] = None, raw_text: Optional[str] = None
):
    try:

        logging.info("🔍 Extracting job metadata from URL or raw text...")

        # Agar tu poora raw_text file mein save karwana chahta hai dekhne ke liye:
        if raw_text:
            logging.info(f"📄 RAW TEXT RECEIVED:\n{'-'*40}\n{raw_text}\n{'-'*40}")
        content_to_process = ""

        # 1. Agar Raw Text hai toh direct use karo
        if raw_text:
            content_to_process = raw_text

        # 2. Agar URL hai toh Firecrawl use karo
        elif url:
            firecrawl_url = "https://api.firecrawl.dev/v1/scrape"
            headers = {
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "url": url,
                "formats": [
                    "markdown"
                ],  # Markdown extraction clean hoti hai LLMs ke liye
                "onlyMainContent": True,  # Kachra (headers/footers) hata deta hai
            }

            async with httpx.AsyncClient(timeout=45.0) as client:
                fc_response = await client.post(
                    firecrawl_url, headers=headers, json=data
                )

                if fc_response.status_code == 200:
                    result = fc_response.json()
                    # Firecrawl ka content 'data.markdown' mein hota hai
                    content_to_process = result.get("data", {}).get("markdown", "")
                else:
                    print(
                        f"Firecrawl Error: {fc_response.status_code} - {fc_response.text}"
                    )
                    raise ValueError(
                        f"Firecrawl couldn't access the site. Error {fc_response.status_code}"
                    )

        if not content_to_process:
            raise ValueError("No content found to extract.")

        # Groq Extraction (Prompt wahi rahega jo pehle tha)
        system_prompt = """
        You are an expert HR data extractor.
        Read the provided job description and extract the following information strictly in JSON format.
        Do NOT wrap the JSON in markdown blocks. Output only raw JSON.

        Required JSON format:
        {
            "title": "Job Title",
            "company": "Company Name",
            "tech_stack": ["Skill 1", "Skill 2"],
            "hiring_manager": "Name if mentioned, else null",
            "vibe": "One short phrase summarizing the vibe/culture"
        }
        """

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            # "llama-3.3-70b-versatile"
            #  "llama-3.1-8b-instant",
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Extract info from this job posting:\n\n{content_to_process[:6000]}",
                },
            ],
            "temperature": 0.8,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            groq_response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            groq_data = groq_response.json()
            print(f"Groq Extraction Response: {groq_data}")
            raw_json = groq_data["choices"][0]["message"]["content"]

            parsed_data = json.loads(raw_json)
            # URL save karna mat bhulna agar wo passed thi
            parsed_data["url"] = url if url else ""
            save_tracked_job(parsed_data)
            return parsed_data

    except Exception as e:
        print(f"Extractor Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

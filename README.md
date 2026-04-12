
# 🧠 Voldie Backend

Welcome to the intelligence layer of **voldie backend**. This is a highly optimized FastAPI backend powered by advanced RAG (Retrieval-Augmented Generation) pipelines to scan, extract, and analyze the tech job market.

## 🚀 Features
* **Hybrid Web Scraping:** Uses Jina.ai for LinkedIn bypass and Firecrawl for deep reading startup career pages.
* **Dual AI Routing:** Fast JSON extraction via QWEN and deep-reasoning RAG pipeline.
* **Smart Scout:** Powered by Tavily Search API to bypass SEO junk and find real job postings.
* **Backdoor "Sniper Mode":** Supports both dynamic vibe-based searches and exact custom queries.

## 🛠️ Tech Stack
* **Framework:** FastAPI / Python 3.x
* **AI/LLM Engine:** Groq (Llama 3.3 70B / 8B) QWEN3.5-plus
* **Search & Scrape:** Tavily, Jina.ai, Firecrawl
* **Database:** Supabase (PostgreSQL)

## 💻 Local Setup

**1. Clone the repository & enter the backend directory**
```bash
git clone <your-repo-url>
cd voldie-backend

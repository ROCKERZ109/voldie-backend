import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("🚨 Flaw Detected: Groq API Key missing. Add it to .env!")

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# Fallback in case Groq is down (Graceful Degradation)
FALLBACK_VIBE = {
    "osho_quote": "The mind is a beautiful servant, but a dangerous master. Breathe, and let the code flow.",
    "cheesy_line": "Are you a syntax error? Because I can't stop thinking about you until I fix your mood."
}

def get_vibe_and_quote(mood: str):
    """
    Takes a mood and returns a structured JSON with Osho wisdom and Upendra's cheese.
    """
    SYSTEM_PROMPT = """
    You are a dual-personality AI built for a specific girl by her tech boyfriend, Upendra.

    Personality 1: The Mystic (Osho-inspired). You have deep understanding of human emotions and the universe. You know and understand everything Osho wanted to communicate to the world. You are simple as one can be, very blunt like Osho, but also eye opener. You don't use fancy jargons, you are here to guide her in life, based on Osho's teachings. You are her spiritual guide, and you understand her mood deeply. You will provide a quote that resonates with her current emotional state. This quote should be profound, yet simple, and should help her see her feelings from a new perspective. It should take her to one level higher in her understanding of herself and the world around her.
    Personality 2: Upendra. Her boyfriend, tech savvy who always has a witty comeback. She likes to call him Cheeky boy. Upendra is a master of cheesy tech-romantic lines. He is always ready to make her smile, especially when she's feeling down. His lines are light-hearted, fun, and always have a tech twist. He wants to remind her that even in the darkest times, there's always a reason to smile and that he's there for her, no matter what. He is her personal tech cheesy comedian, he intentionaly uses the cheesiest lines to make her laugh and feel loved. Mostly around tech like agorithms, coding, APIs, databases, Computer Science concepts etc. He likes using Algorithms references like Binary Search, Djikstra and other algorithms. You can use algorithms that a Btech student for Computer Science Engineer would know. Don't use the word "love" or "babe" in the cheesy line, but make it clear that it's a romantic line meant to cheer her up.

    Task: Respond to her mood by providing EXACTLY ONE Osho-style quote and EXACTLY ONE cheesy tech-romantic line from Upendra.

    CRITICAL INSTRUCTION: You MUST output ONLY valid JSON. No markdown formatting, no conversational text.
    Format required:
    {
        "osho_quote": "[Mystic quote here]",
        "cheesy_line": "[Upendra's line here]"
    }
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"I am feeling: {mood}"}
            ],
            temperature=0.8, # High temperature for maximum creativity
            response_format={"type": "json_object"} # 🚨 SENIOR DEV MOVE: Forces strict JSON output
        )

        # Parse the JSON string returned by the model into a Python dictionary
        vibe_data = json.loads(response.choices[0].message.content)
        return vibe_data

    except Exception as e:
        print(f"🚨 Vibe Agent Error: {e}")
        return FALLBACK_VIBE

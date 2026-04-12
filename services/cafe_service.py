import random
from utils.database import get_db

db = get_db()

FALLBACK_CAFE = {
    "name": "Da Matteo (Magasinsgatan)",
    "address": "Magasinsgatan 17A",
    "why_go_there": "The database is taking a nap, but Da Matteo's coffee never fails. It's a classic Gothenburg safe haven."
}

def get_mood_lifting_cafe():
    """
    Fetches a random active cafe from the secret backdoor DB.
    """
    try:
        # Querying Supabase: SELECT * FROM secret_cafes WHERE is_active = TRUE
        response = db.table('secret_cafes').select('*').eq('is_active', True).execute()
        cafes = response.data

        if not cafes:
            return FALLBACK_CAFE

        # Select a random cafe from the active ones
        selected_cafe = random.choice(cafes)
        return {
            "name": selected_cafe['name'],
            "address": selected_cafe['address'],
            "why_go_there": selected_cafe['why_go_there']
        }

    except Exception as e:
        print(f"🚨 Cafe Service Error: {str(e)}")
        return FALLBACK_CAFE

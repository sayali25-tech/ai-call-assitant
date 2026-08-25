import os
import base64
import tempfile
import asyncio
import re
from fastapi import FastAPI, Request
from groq import Groq
import edge_tts

app = FastAPI()

# ============================================================
# 1. CONFIGURATION
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a helpful customer care assistant for an Indian company.
IMPORTANT: Reply in the EXACT SAME LANGUAGE that the user speaks. 
If the user speaks in Marathi, reply in Marathi. 
If the user speaks in English, reply in English.
Keep responses very short (2-3 sentences), clear, and friendly.
If you don't know something, say you'll check and get back to them."""

# ============================================================
# 2. HELPER: DETECT MARATHI (Devanagari script)
# ============================================================
def is_marathi(text):
    for char in text:
        if '\u0900' <= char <= '\u097F':
            return True
    return False

# ============================================================
# 3. GET AI REPLY (Groq - FREE)
# ============================================================
def get_ai_reply(user_text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return "I'm sorry, I'm having trouble connecting right now. Please try again."

# ============================================================
# 4. TEXT-TO-SPEECH (Edge TTS - FREE)
# ============================================================
async def generate_audio(text):
    voice = "mr-IN-AarohiNeural" if is_marathi(text) else "en-IN-NeerjaNeural"
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_file.name)
        with open(temp_file.name, "rb") as f:
            audio_data = f.read()
        return base64.b64encode(audio_data).decode()
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

# ============================================================
# 5. WEBHOOK ENDPOINT (Vobiz sends POST requests here)
# ============================================================
@app.post("/webhook")
async def webhook(request: Request):
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult")
    
    if not speech_result:
        # Welcome message
        welcome_text = "Hello! Welcome to our customer care. How can I help you today? You can speak in English or Marathi."
        audio_b64 = await generate_audio(welcome_text)
        return {
            "audio": audio_b64,
            "gather": True,
            "gather_timeout": 5,
            "gather_language": "en-IN"
        }
    
    ai_reply = get_ai_reply(speech_result)
    audio_b64 = await generate_audio(ai_reply)
    
    return {
        "audio": audio_b64,
        "gather": True,
        "gather_timeout": 5,
        "gather_language": "en-IN"
    }

# ============================================================
# 6. HEALTH CHECK
# ============================================================
@app.get("/")
async def health():
    return {"status": "ok", "message": "AI Call Center with Marathi & English support!"}
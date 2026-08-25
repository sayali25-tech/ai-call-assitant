import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse, Response
from groq import Groq

# ============================================================
# 1. SET UP AI
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a helpful customer care assistant for an Indian company.
Keep responses very short (2-3 sentences), clear, and friendly. Speak in English."""

conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

app = FastAPI()

# ============================================================
# 2. TWILIO WEBHOOK (RETURNS XML)
# ============================================================
@app.post("/webhook", response_class=PlainTextResponse)
async def webhook(
    SpeechResult: str = Form(None),
    CallStatus: str = Form(None)
):
    # Twilio sends data as form-data, not JSON.

    # Initial Call: No speech yet, ask the user to speak
    if not SpeechResult:
        twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Gather input="speech" timeout="5" language="en-IN">
                <Say voice="alice" language="en-IN">Hello! How can I help you today?</Say>
            </Gather>
        </Response>"""
        return Response(content=twiml_response, media_type="application/xml")

    # End call if user says bye
    user_text = SpeechResult
    print(f"User said: {user_text}") # Logs for debugging on Render

    if any(word in user_text.lower() for word in ["bye", "exit", "goodbye"]):
        return """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="alice" language="en-IN">Thank you for calling. Have a great day!</Say>
        </Response>"""

    # Get AI response from Groq
    conversation.append({"role": "user", "content": user_text})
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=conversation,
            temperature=0.7,
            max_tokens=150
        )
        reply = response.choices[0].message.content
        conversation.append({"role": "assistant", "content": reply})
    except Exception as e:
        reply = "I'm sorry, I'm having trouble connecting."
        print(f"AI Error: {e}")

    # Return TwiML to speak the AI's response using Indian English voice
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Say voice="alice" language="en-IN">{reply}</Say>
        <Redirect>/webhook</Redirect>
    </Response>"""

# Health check (For UptimeRobot)
@app.get("/")
def read_root():
    return {"status": "ok"}

# ============================================================
# RUN SERVER
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

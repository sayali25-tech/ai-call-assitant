import os
from groq import Groq
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# 1. SET UP AI
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a helpful customer care assistant for an Indian company.
Keep responses very short (2-3 sentences), clear, and friendly. Speak in English."""

conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
app = FastAPI()

# 2. VAPI WEBHOOK
@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    print(f"VAPI PAYLOAD: {payload}") 

    message = payload.get("message", {})
    user_text = message.get("transcript") or message.get("text")

    if not user_text:
        return JSONResponse(content={"response": "Hello! How can I help you today?"})

    if any(word in user_text.lower() for word in ["bye", "exit", "goodbye"]):
        return JSONResponse(content={"response": "Thank you for calling. Have a great day!"})

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

    return JSONResponse(content={"response": reply})

@app.get("/")
def read_root():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

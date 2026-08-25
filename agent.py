import os
import tempfile
import time
import asyncio
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from groq import Groq
import edge_tts
import pygame  # This now works with pygame-ce

# ============================================================
# 1. PUT YOUR API KEY HERE
# ============================================================
GROQ_API_KEY = "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"  # <-- REPLACE with your actual key

# ============================================================
# 2. SET UP THE AI'S PERSONALITY
# ============================================================
SYSTEM_PROMPT = """You are a helpful customer care assistant for an Indian company.
Keep responses very short (2-3 sentences), clear, and friendly. Speak in English.
If you don't know something, say you'll check and get back to them."""

# Conversation memory
conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

# Connect to Groq
client = Groq(api_key=GROQ_API_KEY)

# ============================================================
# 3. FUNCTION: RECORD AUDIO FROM MICROPHONE
# ============================================================
def record_audio(duration=5, samplerate=16000):
    print("\n🎤 Listening... (speak for 5 seconds)")
    recording = sd.rec(
        int(duration * samplerate),
        samplerate=samplerate,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    print("✅ Stopped listening.")
    return recording.flatten().astype(np.int16)

# ============================================================
# 4. FUNCTION: CONVERT SPEECH TO TEXT (STT) - FREE via Groq
# ============================================================
def transcribe_audio(audio_data, samplerate=16000):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        wav.write(tmp.name, samplerate, audio_data)
        tmp_path = tmp.name
    
    with open(tmp_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            file=(tmp_path, f.read()),
            model="whisper-large-v3",
            language="en"
        )
    
    os.unlink(tmp_path)
    return transcript.text

# ============================================================
# 5. FUNCTION: CONVERT TEXT TO SPEECH (TTS) - FREE via Edge TTS
# ============================================================
async def speak_text(text):
    print(f"\n🤖 AI: {text}")
    
    # Create a temporary MP3 file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()
    
    # Generate speech
    communicate = edge_tts.Communicate(text, voice="en-IN-NeerjaNeural")
    await communicate.save(temp_file.name)
    
    # Play the audio using pygame
    pygame.mixer.init()
    pygame.mixer.music.stop()          # <-- Stops any previous audio
    pygame.mixer.music.load(temp_file.name)
    pygame.mixer.music.play()
    
    # Wait for playback to finish
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)       # <-- Use asyncio.sleep, not time.sleep
    
    pygame.mixer.quit()
    os.unlink(temp_file.name)
# ============================================================
# 6. MAIN FUNCTION: RUN THE LOOP
# ============================================================
async def main():
    print("\n" + "="*50)
    print("🤖 AI CUSTOMER CARE ASSISTANT")
    print("📞 Say 'bye' or 'exit' to end")
    print("="*50 + "\n")
    
    while True:
        audio = record_audio(duration=5)
        
        try:
            user_text = transcribe_audio(audio)
            if not user_text.strip():
                print("⚠️  I didn't hear anything. Please try again.")
                continue
            print(f"🗣️  You said: {user_text}")
        except Exception as e:
            print(f"⚠️  Transcription error: {e}")
            continue
        
        if any(word in user_text.lower() for word in ["bye", "exit", "goodbye"]):
            await speak_text("Thank you for calling. Have a great day!")
            break
        
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
            reply = "I'm sorry, I'm having trouble connecting. Please try again."
            print(f"⚠️  AI Error: {e}")
        
        await speak_text(reply)

# ============================================================
# 7. RUN THE ASSISTANT
# ============================================================
if __name__ == "__main__":
    asyncio.run(main())
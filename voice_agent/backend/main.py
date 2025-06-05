import os
import uuid
import tempfile
import asyncio
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

app = FastAPI()

# Add route to serve the test WebSocket HTML file
@app.get("/test", response_class=HTMLResponse)
async def get_test_html():
    with open("test_websocket.html") as f:
        return HTMLResponse(content=f.read())

# Allow CORS for frontend - be explicit about origins for WebSockets
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*", "GET", "POST"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# In-memory session context (for demo; use Redis for production)
session_context: Dict[str, List[Dict]] = {}

# --- Helper Functions ---
async def transcribe_with_whisper_api(audio_path: str) -> str:
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    # Check file size
    file_size = os.path.getsize(audio_path)
    print(f"Audio file size: {file_size} bytes")
    if file_size < 100:  # Too small to be valid audio
        return "[Audio too short to transcribe]"
    
    # Use appropriate content type based on file extension
    content_type = "audio/webm" if audio_path.endswith(".webm") else "audio/wav"
    print(f"Using content type: {content_type} for file {audio_path}")
    
    try:
        # Try to convert to mp3 first if ffmpeg is available (more reliable with Whisper)
        mp3_path = None
        try:
            import subprocess
            mp3_path = audio_path.replace(".webm", ".mp3").replace(".wav", ".mp3")
            print(f"Converting audio to mp3 at {mp3_path}")
            subprocess.run(["ffmpeg", "-i", audio_path, "-acodec", "libmp3lame", "-q:a", "4", mp3_path], 
                          check=True, capture_output=True, timeout=10)
            
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 100:
                audio_path = mp3_path
                content_type = "audio/mp3"
                print(f"Successfully converted to MP3, size: {os.path.getsize(mp3_path)} bytes")
        except Exception as e:
            print(f"MP3 conversion failed, using original format: {str(e)}")
    
        with open(audio_path, "rb") as audio_file:
            files = {"file": (os.path.basename(audio_path), audio_file, content_type)}
            data = {"model": "whisper-1", "language": "en"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                print("Sending request to Whisper API...")
                resp = await client.post(url, headers=headers, files=files, data=data)
                resp.raise_for_status()
                result = resp.json()["text"]
                print(f"Transcription successful: {result}")
                return result
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        if isinstance(e, httpx.HTTPStatusError):
            print(f"Response content: {e.response.content}")
        # Return error message
        return "[Could not transcribe audio - check server logs]"

async def gpt4o_response(context: List[Dict], whisper_text: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    messages = context + [{"role": "user", "content": whisper_text}]
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def elevenlabs_tts(text: str) -> bytes:
    # Use streaming endpoint with specified voice ID
    voice_id = "zgqefOY5FPQ3bB7OZTVR"  # The specific voice ID provided
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "output_format": "mp3_44100_128",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        print(f"ElevenLabs TTS error: {str(e)}")
        # Return empty bytes if there's an error to avoid crashing the WebSocket
        return b""

@app.websocket("/ws/voice-chat")
async def voice_chat_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    session_context[session_id] = []
    is_speaking = False  # Track if the AI is currently speaking
    try:
        while True:
            # Receive either text control messages or audio bytes
            message = await websocket.receive()

            # Handle text control messages
            if "text" in message:
                text_msg = message.get("text", "")
                if text_msg == "CLIENT_DONE_PLAYING":
                    # Frontend reports that playback is finished, allow next recording
                    is_speaking = False
                    await websocket.send_text("[Status] CLIENT_READY")
                    print("Client ready for next turn")
                elif text_msg == "PAUSE_PROCESSING":
                    # Frontend detected a pause and is sending audio for processing
                    # but wants to continue listening after processing
                    print("Received PAUSE_PROCESSING signal - will process audio but keep connection open")
                    # The next message should be the audio blob
                    # We'll handle it in the regular flow, but remember it's a pause
                    continue
                # Ignore other text messages here
                continue

            # Handle binary audio data
            if "bytes" not in message:
                # Nothing to process
                continue

            if is_speaking:
                # Currently speaking – ignore any incoming audio
                print("Ignoring audio chunk while AI is speaking (frontend should not send during playback)")
                continue

            data = message["bytes"]
            
            # Buffer audio chunks until user stops speaking (short pause)
            audio_chunks = [data]
            CHUNK_TIMEOUT = 2.0
            websocket._loop = asyncio.get_event_loop()
            last_chunk_time = websocket._loop.time()
            
            while True:
                try:
                    # Create named tasks so we can properly clean up
                    receive_task = asyncio.create_task(websocket.receive(), name="receive_bytes")
                    timeout_task = asyncio.create_task(asyncio.sleep(CHUNK_TIMEOUT), name="timeout")
                    
                    # Wait for either receive or timeout
                    done, pending = await asyncio.wait(
                        [receive_task, timeout_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks to avoid resource leaks
                    for task in pending:
                        task.cancel()
                    
                    # Check which task completed
                    for task in done:
                        if task.get_name() == "receive_bytes" and not task.cancelled():
                            audio_chunks.append(task.result()["bytes"])
                            last_chunk_time = websocket._loop.time()
                        elif task.get_name() == "timeout":
                            # If timeout occurred, break out if no recent chunks
                            if (websocket._loop.time() - last_chunk_time) >= CHUNK_TIMEOUT:
                                print(f"Timeout reached after {CHUNK_TIMEOUT}s with no new audio")
                                break
                            break
                    else:
                        break
                except Exception:
                    break

            # Check if this is a pause-processing request
            is_pause_processing = False
            if len(audio_chunks) == 1 and isinstance(message.get("bytes"), bytes):
                # This might be a pause processing request (single chunk sent after PAUSE_PROCESSING message)
                is_pause_processing = True
                print("Processing audio during pause")
            
            # Save audio to temp file - proper handling for WebM format from browser
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(b"".join(audio_chunks))
                audio_path = tmp.name
                
            # Convert to proper format for Whisper if needed
            try:
                import wave
                import subprocess
                wav_path = audio_path.replace(".webm", ".wav")
                # Use ffmpeg if available to convert to proper WAV format
                try:
                    subprocess.run(["ffmpeg", "-i", audio_path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True)
                    audio_path = wav_path
                except (subprocess.SubprocessError, FileNotFoundError):
                    # If ffmpeg fails, we'll try to use the original file
                    await websocket.send_text("[Warning] Audio conversion failed, using original format.")
            except Exception as e:
                await websocket.send_text(f"[Warning] Audio processing error: {str(e)}")
                # Continue with original file

            # 1. Whisper API (OpenAI)
            transcript = await transcribe_with_whisper_api(audio_path)
            await websocket.send_text(f"[Transcript] {transcript}")
            
            # Skip processing if the transcript is empty or too short (likely just noise/silence)
            # Also skip if it contains common silence indicators from Whisper
            if not transcript or len(transcript.strip()) < 3 or transcript.lower() in [
                "[could not transcribe audio]", 
                "[audio too short to transcribe]",
                "you",
                "um",
                "uh",
                "hmm"
            ]:
                if is_pause_processing:
                    # If this was a pause processing request, tell the client we're done
                    # processing the pause but didn't generate a response
                    await websocket.send_text("[Status] PAUSE_PROCESSED")
                    print(f"Pause processing skipped for empty/short input: '{transcript}'")
                else:
                    # Regular empty input handling
                    await websocket.send_text("[Status] SKIPPING_EMPTY_INPUT")
                    print(f"Skipping processing for empty/short input: '{transcript}'")
                continue

            # 2. GPT-4o mini for chat response
            context = session_context[session_id]
            ai_response = await gpt4o_response(context, transcript)
            await websocket.send_text(f"[AI] {ai_response}")
            # Update context
            session_context[session_id].append({"role": "user", "content": transcript})
            session_context[session_id].append({"role": "assistant", "content": ai_response})

            # Set speaking flag to prevent processing audio during playback
            is_speaking = True
            try:
                await websocket.send_text("[Status] AI_SPEAKING")

                # 3. ElevenLabs TTS
                tts_audio = await elevenlabs_tts(ai_response)
                await websocket.send_bytes(tts_audio)
                
                # Only send this if we successfully sent the audio
                try:
                    await websocket.send_text("[Status] AI_DONE_SPEAKING")
                except RuntimeError as e:
                    if "close message has been sent" in str(e):
                        print("WebSocket already closed, cannot send status message")
                    else:
                        raise
            finally:
                # Make sure we always reset the speaking flag
                is_speaking = False

            # For pause processing, we need to tell the frontend we're done
            # so it can continue listening
            if is_pause_processing:
                await websocket.send_text("[Status] PAUSE_PROCESSED")
                print("Pause processing complete, client can continue listening")
            # Otherwise, wait for frontend to confirm playback done before next utterance

    except WebSocketDisconnect:
        del session_context[session_id]

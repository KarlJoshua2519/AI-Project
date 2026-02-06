import cv2
import json
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time
import subprocess
import os
import asyncio
import edge_tts
import requests
import base64

from openai import OpenAI
from dotenv import load_dotenv
import os
import json

# Persistent Memory Path
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return {"user_facts": {}}

def save_memory(memory_data):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory_data, f, indent=4)

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# AI Configuration (Switching from DeepSeek to Ollama)
model_id = "llama3" 
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama", # Ollama doesn't need a real key
)
print(f">>> Local AI (Ollama) Initialized with {model_id}")

# Shared data
robot_data = {
    "x": 0.5,
    "y": 0.5,
    "emotion": "neutral",
    "mouth_open": 0,
    "eye_blink": False,
    "last_command": "",
    "chat_response": "",
    "audio_level": 0,
    "audio_file": "response_1.mp3"
}

# Cooldown for Quota
quota_cooldown_until = 0

# Conversation Memory
chat_history = []
chat_session = None

system_instruction = ""

def init_chat():
    global system_instruction
    if client:
        try:
            memory = load_memory()
            facts_summary = ", ".join([f"{k}: {v}" for k, v in memory['user_facts'].items()])
            
            system_instruction = (
                "You are P-Bot, an intelligent and cute screen robot. "
                "Keep all responses to exactly one short sentence. "
                "Be friendly, polite, and slightly playful. "
                f"Current user facts: {facts_summary}. "
                "At the end of every response, you MUST include an emotion tag: [EMOTION: happy], [EMOTION: surprised], [EMOTION: thinking], [EMOTION: neutral], or [EMOTION: happy]. "
                "If the user asks to open an app (calculator, notepad, paint, browser), "
                "reply with 'Opening [app name]!' and include the tag '[OPEN: app_identifier]'. "
                "Identifiers: calc, notepad, mspaint, google-chrome, msedge, control. "
                "If the user tells you a new fact (birthday, name, etc.), acknowledge it "
                "and ALWAYS include the tag '[UPDATE_MEMORY: key=value]' before the emotion tag."
            )
            print(">>> DeepSeek Chat system instruction initialized.")
        except Exception as e:
            print(f">>> Chat Initialization Warning: {e}")
    
    # Pre-generate a silent or welcome file to avoid 404s
    threading.Thread(target=generate_speech, args=("System online.",), daemon=True).start()

# init_chat() call removed from here to avoid NameError

# Load OpenCV's built-in face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def listen_speech():
    global robot_data
    while True:
        # Start the PowerShell listener with ExecutionPolicy Bypass
        ps_command = [
            "powershell", 
            "-NoProfile", 
            "-ExecutionPolicy", "Bypass", 
            "-File", "listen.ps1"
        ]
        
        process = subprocess.Popen(
            ps_command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1
        )
        
        print(f">>> Python: Speech Listener Started (PID: {process.pid})")
        
        try:
            for line in process.stdout:
                line = line.strip()
                if not line: continue
                
                if line.startswith("HEARD:"):
                    raw_text = line[6:].strip()
                    command = raw_text.split("(")[0].strip().lower() if "(" in raw_text else raw_text.lower()
                    print(f">>> ROBOT RECOGNIZED: {command}")
                    robot_data["last_command"] = command
                    
                    # If it's not a basic command, ask the AI
                    if client and not any(x in command for x in ["shut down", "power off", "close"]):
                        threading.Thread(target=process_with_ai, args=(command,), daemon=True).start()
                        
                    threading.Thread(target=reset_command, args=(1.0,), daemon=True).start()
                elif "AUDIO_LEVEL:" in line:
                    try:
                        parts = line.split("AUDIO_LEVEL:")[1].strip().split()
                        robot_data["audio_level"] = int(parts[0])
                    except: pass
                elif any(x in line for x in ["ERROR", "REJECTED", "SCRIPT_EXITING"]):
                    print(f">>> PS_LOG: {line}")
                elif "STATUS: LISTENING" in line:
                    print(f">>> PS_LOG: {line}")
        except Exception as e:
            print(f">>> Python: Error reading listener output: {e}")

        process.wait()
        print(f">>> Python: Speech Listener Process Ended (Exit Code: {process.returncode}). Restarting in 2s...")
        time.sleep(2)

def reset_command(delay):
    global robot_data
    time.sleep(delay)
    robot_data["last_command"] = ""

def execute_system_command(tag_content):
    """Executes system commands like opening apps"""
    try:
        app_id = tag_content.lower().strip()
        print(f">>> EXECUTE SYSTEM COMMAND: {app_id}")
        
        if app_id == "calc":
            subprocess.Popen("calc.exe")
        elif app_id == "notepad":
            subprocess.Popen("notepad.exe")
        elif app_id == "mspaint":
            subprocess.Popen("mspaint.exe")
        elif app_id == "google-chrome":
            subprocess.Popen(["start", "chrome"], shell=True)
        elif app_id == "msedge":
            subprocess.Popen(["start", "msedge"], shell=True)
        elif app_id == "control":
            subprocess.Popen("control.exe")
        elif app_id == "cmd":
            subprocess.Popen("start cmd", shell=True)
            
    except Exception as e:
        print(f">>> System Command Error: {e}")

def process_with_ai(text):
    global robot_data, chat_history, quota_cooldown_until, system_instruction
    if not client:
        print(">>> AI Error: Client not initialized")
        return
        
    try:
        print(f">>> ASKING AI (Ollama): {text}")
        
        # Prepare messages
        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(chat_history[-10:])
        messages.append({"role": "user", "content": text})

        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            stream=False
        )
        
        if response and response.choices:
            text_resp = response.choices[0].message.content.strip()
            
            # Update history
            chat_history.append({"role": "user", "content": text})
            chat_history.append({"role": "assistant", "content": text_resp})
            
            # Check for OPEN commands
            if "[OPEN:" in text_resp:
                try:
                    app_tag = text_resp.split("[OPEN:")[1].split("]")[0]
                    execute_system_command(app_tag)
                    text_resp = text_resp.replace(f"[OPEN:{app_tag}]", "").replace(f"[OPEN: {app_tag}]", "")
                except Exception as e:
                    print(f"Error parsing OPEN tag: {e}")
            
            # Simple check for memory updates
            if "[UPDATE_MEMORY:" in text_resp:
                try:
                    parts = text_resp.split("[UPDATE_MEMORY:")[1].split("]")[0].split("=")
                    if len(parts) == 2:
                        key, val = parts[0].strip(), parts[1].strip()
                        mem = load_memory()
                        mem["user_facts"][key] = val
                        save_memory(mem)
                        print(f">>> MEMORY UPDATED: {key} = {val}")
                        text_resp = text_resp.replace(f"[UPDATE_MEMORY: {key}={val}]", "").strip()
                except: pass

            # Check for emotion updates
            if "[EMOTION:" in text_resp:
                try:
                    emotion = text_resp.split("[EMOTION:")[1].split("]")[0].strip().lower()
                    robot_data["emotion"] = emotion
                    print(f">>> EMOTION UPDATED: {emotion}")
                    text_resp = text_resp.split("[EMOTION:")[0].strip()
                except: pass

            print(f">>> AI RESPONSE: {text_resp}")
            
            # Use Friendly TTS
            threading.Thread(target=generate_speech, args=(text_resp,), daemon=True).start()
        else:
            print(">>> AI Error: Empty response")
    except Exception as e:
        error_msg = str(e)
        print(f">>> AI Error: {error_msg}")
        if "Connection" in error_msg:
             robot_data["chat_response"] = "I can't connect to my local brain. Is Ollama running?"
        else:
             robot_data["chat_response"] = "I'm having a bit of trouble thinking right now."

def generate_speech(text):
    """Generates high quality speech using Edge TTS (Ava - Friendly Voice)"""
    VOICE = "en-US-AvaNeural"
    global robot_data
    
    # Toggle between two files to avoid file locking issues in Electron
    current_file = robot_data.get("audio_file", "response_1.mp3")
    next_file = "response_2.mp3" if current_file == "response_1.mp3" else "response_1.mp3"
    
    async def amain():
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(next_file)
    
    try:
        asyncio.run(amain())
        
        # Verify file exists and is not empty before updating data
        if os.path.exists(next_file) and os.path.getsize(next_file) > 0:
            robot_data["audio_file"] = next_file
            robot_data["chat_response"] = text
            print(f">>> FRIENDLY VOICE GENERATED: {next_file} using {VOICE}")
        else:
            print(">>> TTS Error: File was not generated correctly")
            robot_data["chat_response"] = text
    except Exception as e:
        print(f">>> TTS Error: {e}")
        robot_data["chat_response"] = text

def analyze_face():
    global robot_data
    cap = cv2.VideoCapture(0)
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue

        # Flip for mirror effect
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            
            # Center of face (relative 0.0 to 1.0)
            robot_data["x"] = (x + w/2) / frame.shape[1]
            robot_data["y"] = (y + h/2) / frame.shape[0]
            
            # Mouth detection
            roi_gray = gray[y + int(h/2):y + h, x:x + w]
            _, thresh = cv2.threshold(roi_gray, 50, 255, cv2.THRESH_BINARY_INV)
            mouth_pixels = cv2.countNonZero(thresh)
            
            mouth_val = (mouth_pixels / (w * h / 2)) * 100
            robot_data["mouth_open"] = mouth_val
            
            if mouth_val > 5:
                robot_data["emotion"] = "talking"
            else:
                robot_data["emotion"] = "neutral"
                
        time.sleep(0.05)

@app.route('/data')
def get_data():
    return jsonify(robot_data)

@app.route('/chat', methods=['POST'])
def chat():
    from flask import request
    global robot_data
    text = request.json.get('text', '')
    if text and client:
        threading.Thread(target=process_with_ai, args=(text,), daemon=True).start()
        return jsonify({"status": "processing"})
    return jsonify({"status": "error"}), 400

@app.route('/speak', methods=['POST'])
def speak():
    from flask import request
    text = request.json.get('text', '')
    if text:
        threading.Thread(target=generate_speech, args=(text,), daemon=True).start()
        return jsonify({"status": "queued"})
    return jsonify({"status": "error"}), 400

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    global robot_data
    robot_data["chat_response"] = ""
    return jsonify({"status": "cleared"})

if __name__ == '__main__':
    init_chat()
    threading.Thread(target=analyze_face, daemon=True).start()
    threading.Thread(target=listen_speech, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)

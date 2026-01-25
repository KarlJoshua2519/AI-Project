import cv2
import json
from flask import Flask, jsonify
from flask_cors import CORS
import threading
import time
import subprocess
import os

import google.generativeai as genai
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# Shared data
robot_data = {
    "x": 0.5,
    "y": 0.5,
    "emotion": "neutral",
    "mouth_open": 0,
    "eye_blink": False,
    "last_command": "",
    "chat_response": "",
    "audio_level": 0
}

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
                    
                    # If it's not a basic command, ask Gemini
                    if model and not any(x in command for x in ["shut down", "power off", "close"]):
                        threading.Thread(target=process_with_gemini, args=(command,), daemon=True).start()
                        
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

def process_with_gemini(text):
    global robot_data
    if not model:
        return
        
    try:
        # Give context to make it "genius"
        prompt = f"You are P-Bot, an AI robot on the user's screen. The user just said: '{text}'. Respond concisely (1 sentence) and intelligently."
        response = model.generate_content(prompt)
        if response and response.text:
            robot_data["chat_response"] = response.text.strip()
            print(f">>> GEMINI RESPONSE: {robot_data['chat_response']}")
    except Exception as e:
        print(f">>> Gemini Error: {e}")

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

if __name__ == '__main__':
    threading.Thread(target=analyze_face, daemon=True).start()
    threading.Thread(target=listen_speech, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)

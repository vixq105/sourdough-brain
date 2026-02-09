import os
import requests
import json
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# --- CONFIG ---
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GENAI_API_KEY")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER = os.environ.get("LINE_USER_ID")

# รายชื่อโมเดลที่จะไล่เช็ค (จากใหม่ไปเก่า)
MODELS_TO_TRY = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro-vision"  # <--- ตัวความหวังสุดท้าย
]

def send_line(msg):
    if not LINE_TOKEN or not LINE_USER: return
    try:
        requests.post(
            'https://api.line.me/v2/bot/message/push',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_TOKEN}'},
            json={"to": LINE_USER, "messages": [{"type": "text", "text": msg}]}
        )
    except: pass

@app.route('/')
def home():
    return "Sourdough Auto-Switcher Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- New Request (Auto-Model) ---")
    
    if not API_KEY: return "Error|0|Key Missing"
    if 'imageFile' not in request.files: return "Error|0|No Image"
    
    file = request.files['imageFile']
    try:
        # เตรียมรูปครั้งเดียว
        img_data = base64.b64encode(file.read()).decode('utf-8')
        
        last_error = ""
        success_result = None
        used_model = ""

        # --- ลูปเพื่อลองโมเดลทีละตัว ---
        for model_name in MODELS_TO_TRY:
            print(f"Trying model: {model_name}...")
            
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
            headers = {'Content-Type': 'application/json'}
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Analyze sourdough. Return strictly ONE line: Status|Time(mins)|Advice. Status: Ready, Peak, Hungry, Moldy. Example: Ready|0|Bake now"},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_data}}
                    ]
                }]
            }

            resp = requests.post(api_url, headers=headers, json=payload)
            resp_json = resp.json()

            # ถ้าเจอ Error ให้ข้ามไปตัวถัดไป
            if 'error' in resp_json:
                error_msg = resp_json['error'].get('message', '')
                print(f"Failed {model_name}: {error_msg}")
                last_error = error_msg
                continue # ไปรอบถัดไป
            
            # ถ้าสำเร็จ!
            if 'candidates' in resp_json:
                try:
                    success_result = resp_json['candidates'][0]['content']['parts'][0]['text']
                    used_model = model_name
                    break # ออกจากลูปทันที
                except:
                    last_error = "Bad Response Format"
                    continue

        # --- สรุปผล ---
        if success_result:
            clean_result = success_result.strip().replace('\n', '').replace('*', '')
            print(f"Success with {used_model}: {clean_result}")
            
            if any(x in clean_result for x in ["Ready", "Peak", "Moldy"]):
                 send_line(f"🍞 ({used_model})\n{clean_result}")
            
            return clean_result
        else:
            # ถ้าลองทุกตัวแล้วยังพัง
            print("All models failed.")
            return f"Error|0|{last_error[:20]}"

    except Exception as e:
        print(traceback.format_exc())
        return f"Error|0|Sys: {str(e)[:15]}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

import os
import requests
import json
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# --- 1. หา Key แบบกันพลาด (ลองทั้ง 2 ชื่อ) ---
# ลองดึงชื่อแรก
API_KEY = os.environ.get("GEMINI_API_KEY")
# ถ้าไม่มี ลองดึงชื่อที่สอง (เผื่อคุณตั้งชื่อนี้ไว้)
if not API_KEY:
    API_KEY = os.environ.get("GENAI_API_KEY")

LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

def send_line_alert(msg):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID: return
    try:
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_TOKEN}'}
        data = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": msg}]}
        requests.post(url, headers=headers, data=json.dumps(data))
    except: pass

@app.route('/')
def home():
    if not API_KEY:
        return "Warning: API KEY Missing in Render!"
    return f"Direct API Mode (Key found: {API_KEY[:5]}...)"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- Direct API Request ---")
    
    # 1. เช็ค Key ก่อนเลย
    if not API_KEY:
        return "Error|0|Key Missing in Server"

    # 2. เช็ครูป
    if 'imageFile' not in request.files:
        return "Error|0|No Image Sent"
    
    file = request.files['imageFile']
    
    try:
        # เตรียมข้อมูล
        image_bytes = file.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # ยิงไปที่ Google (ใช้ 1.5-flash)
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze sourdough. Return strictly ONE line: Status|Time(mins)|Advice. Status: Ready, Peak, Hungry, Moldy. Example: Ready|0|Bake now"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                ]
            }]
        }

        # ส่ง request
        print("Sending to Google...")
        response = requests.post(api_url, headers=headers, json=payload)
        response_json = response.json()

        # --- 3. จุดตัดสินสำคัญ: เช็ค Error จาก Google ---
        if 'error' in response_json:
            error_msg = response_json['error'].get('message', 'Unknown Error')
            print(f"GOOGLE REFUSED: {error_msg}")
            
            # ส่ง Error จริงกลับไปโชว์ที่จอ ESP32 (ตัดให้สั้นลง)
            short_err = error_msg[:20] 
            return f"Error|0|{short_err}"

        # ถ้าผ่าน
        if 'candidates' in response_json:
            result = response_json['candidates'][0]['content']['parts'][0]['text']
            result = result.strip().replace('\n', '').replace('*', '')
            print(f"Success: {result}")
            
            # ส่งไลน์
            if any(x in result for x in ["Ready", "Peak", "Moldy"]):
                 send_line_alert(f"🍞 ผลการตรวจ: {result}")
            
            return result
        else:
            return "Error|0|No Answer from AI"

    except Exception as e:
        print(traceback.format_exc())
        return f"Error|0|Sys: {str(e)[:15]}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

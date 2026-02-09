import os
import requests
import json
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# --- 1. หา Key แบบกันพลาด ---
API_KEY = os.environ.get("GEMINI_API_KEY")
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
    if not API_KEY: return "Warning: NO API KEY"
    return "Sourdough Direct-API (v1.5-001) Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- Request (Full Version ID) ---")
    
    if not API_KEY: return "Error|0|Key Missing"
    if 'imageFile' not in request.files: return "Error|0|No Image"
    
    file = request.files['imageFile']
    
    try:
        image_b64 = base64.b64encode(file.read()).decode('utf-8')

        # ⚠️ จุดแก้สำคัญ: ใช้ชื่อเต็ม 'gemini-1.5-flash-001'
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-001:generateContent"
        
        # ⚠️ จุดแก้สำคัญ: ย้าย Key มาใส่ใน Header (x-goog-api-key)
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': API_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze sourdough image. Return strictly ONE line: Status|Time(mins)|Advice. Status: Ready, Peak, Hungry, Moldy. Example: Ready|0|Bake now"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
                ]
            }]
        }

        print(f"Sending to: {api_url}...")
        response = requests.post(api_url, headers=headers, json=payload)
        response_json = response.json()

        # เช็ค Error แบบละเอียด
        if 'error' in response_json:
            err_msg = response_json['error'].get('message', 'Unknown')
            print(f"Google Error: {err_msg}")
            
            # ถ้ายังหา 1.5-flash-001 ไม่เจอ ให้ลองถอยไป 1.5-pro (ยอมช้านิดนึงแต่ชัวร์)
            if "not found" in err_msg or "404" in str(response.status_code):
                 return "Error|0|Try gemini-1.5-pro"
            
            return f"Error|0|{err_msg[:20]}"

        # ดึงคำตอบ
        if 'candidates' in response_json:
            result = response_json['candidates'][0]['content']['parts'][0]['text']
            result = result.strip().replace('\n', '').replace('*', '')
            print(f"Success: {result}")
            
            if any(x in result for x in ["Ready", "Peak", "Moldy"]):
                 send_line_alert(f"🍞 {result}")
            
            return result
        else:
            return "Error|0|No AI Response"

    except Exception as e:
        print(traceback.format_exc())
        return f"Error|0|Sys: {str(e)[:15]}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

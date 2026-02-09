import os
import requests
import json
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจ ---
# พยายามหา Key ทุกชื่อที่เป็นไปได้
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
    return "Sourdough Monitor (v1.5 PRO) Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- Request (Gemini 1.5 Pro) ---")
    
    if not API_KEY: return "Error|0|Key Missing"
    if 'imageFile' not in request.files: return "Error|0|No Image"
    
    file = request.files['imageFile']
    
    try:
        # แปลงรูปเป็น Base64
        image_b64 = base64.b64encode(file.read()).decode('utf-8')

        # ⚠️ เปลี่ยนมาใช้ 'gemini-1.5-pro' (ตัวท็อปสุด)
        # ใช้ v1beta endpoint ที่รองรับ free tier ได้ดีกว่า
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze this sourdough starter image. Return strictly ONE line: Status|TimeRemaining(mins)|ShortAdvice. Status options: Ready, Peak, Hungry, Moldy, Sleepy. Example: Ready|0|Bake now"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    }
                ]
            }]
        }

        print("Sending to Gemini 1.5 Pro...")
        response = requests.post(api_url, headers=headers, json=payload)
        response_json = response.json()

        # เช็ค Error จาก Google
        if 'error' in response_json:
            err_msg = response_json['error'].get('message', 'Unknown')
            print(f"GOOGLE ERROR: {err_msg}")
            
            # ส่ง Error กลับไปโชว์ที่จอ (เช่น API Key หมดอายุ, หรือยังไม่เปิดใช้ API)
            return f"Error|0|{err_msg[:20]}"

        # ดึงคำตอบ
        if 'candidates' in response_json:
            result = response_json['candidates'][0]['content']['parts'][0]['text']
            result = result.strip().replace('\n', '').replace('*', '')
            print(f"Success: {result}")
            
            # ส่ง LINE ถ้าจำเป็น
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

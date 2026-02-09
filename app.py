import os
import requests
import json
import base64
import traceback
from flask import Flask, request

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจ ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# --- 2. ฟังก์ชันส่ง LINE ---
def send_line_alert(message):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID: return
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_TOKEN}'
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try: requests.post(url, headers=headers, data=json.dumps(data))
    except: pass

@app.route('/')
def home():
    return "Sourdough Direct-API Mode Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- New Direct Request ---")
    
    # 1. รับรูปจาก ESP32
    if 'imageFile' not in request.files:
        return "Error|0|No Image Sent"
    
    file = request.files['imageFile']
    
    try:
        # แปลงรูปเป็นรหัส Base64 (เพื่อส่งแนบจดหมายไปหา Google)
        image_bytes = file.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # --- 3. ยิงตรงไปหา Google (ไม่ผ่าน Library) ---
        # ใช้โมเดล gemini-1.5-flash ได้แน่นอน เพราะเราเรียก URL โดยตรง
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Analyze this sourdough starter. Return strictly ONE line: Status|TimeRemaining(mins)|ShortAdvice. Status options: Ready, Peak, Hungry, Moldy, Sleepy. Example: Ready|0|Bake now"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    }
                ]
            }]
        }

        # ส่งข้อมูลออกไป
        response = requests.post(api_url, headers=headers, json=payload)
        response_json = response.json()

        # เช็คว่ามี Error จาก Google ไหม
        if 'error' in response_json:
            print(f"Google API Error: {response_json['error']}")
            return f"Error|0|API Error"

        # ดึงคำตอบออกมา
        try:
            result_text = response_json['candidates'][0]['content']['parts'][0]['text']
            result_text = result_text.strip().replace('\n', '').replace('```', '')
            print(f"AI Says: {result_text}")
        except:
            return "Error|0|Bad AI Response"

        # --- 4. ส่ง LINE ---
        if any(x in result_text for x in ["Ready", "Peak", "Moldy"]):
            emoji = "🍞"
            if "Moldy" in result_text: emoji = "⚠️ ราขึ้น!"
            elif "Ready" in result_text or "Peak" in result_text: emoji = "✅ ฟูสวยแล้ว!"
            
            parts = result_text.split('|')
            status_show = parts[0] if len(parts) > 0 else result_text
            
            send_line_alert(f"{emoji}\nสถานะ: {status_show}\n(ไปดูน้องด่วน!)")

        return result_text

    except Exception as e:
        print(f"System Error: {traceback.format_exc()}")
        return f"Error|0|System Fail"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

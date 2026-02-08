import os
import requests
import json
import traceback
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจ (ดึงจาก Render) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ตั้งค่า AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ใช้โมเดลนี้ครับ (ต้องแก้ requirements.txt ก่อนถึงจะใช้ได้)
MODEL_NAME = 'models/gemini-1.5-flash'

# --- 2. ฟังก์ชันส่ง LINE ---
def send_line_alert(message):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        print("LINE keys missing")
        return

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_TOKEN}'
    }
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        requests.post(url, headers=headers, data=json.dumps(data))
        print("LINE Sent!")
    except Exception as e:
        print(f"LINE Error: {e}")

@app.route('/')
def home():
    return "Sourdough Monitor is Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- New Request ---")
    
    # 1. รับรูป
    if 'imageFile' not in request.files:
        return "Error|0|No Image"
    
    file = request.files['imageFile']

    try:
        # 2. เรียก AI
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = """
        Analyze this sourdough starter image.
        Strictly return ONE line in this format using pipe '|' separator:
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: Ready, Peak, Hungry, Moldy, Sleepy.
        TimeRemaining: integer (0 if ready).
        ShortAdvice: Max 6 words.
        Example: Ready|0|Bake now!
        """
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": file.read()}
        ])
        
        result = response.text.strip().replace('```', '').replace('\n', '')
        print(f"AI: {result}")

        # 3. ส่ง LINE (ถ้าสถานะสำคัญ)
        # เช็คว่ามีคำว่า Ready, Peak หรือ Moldy ไหม
        if any(x in result for x in ["Ready", "Peak", "Moldy"]):
            emoji = "🍞"
            if "Moldy" in result: emoji = "⚠️ ราขึ้น!"
            elif "Ready" in result: emoji = "✅ พร้อมแล้ว!"
            
            # แยกข้อความเพื่อความสวยงาม
            parts = result.split('|')
            status_show = parts[0] if len(parts) > 0 else result
            
            msg = f"{emoji}\nสถานะ: {status_show}\n(รีบไปดูที่ตู้ด่วน!)"
            send_line_alert(msg)

        # ส่งค่ากลับไปโชว์ที่จอ ESP32
        return result

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        # จัดการ Error แบบต่างๆ
        err_msg = str(e)
        if "404" in err_msg: return "Error|0|Update Requirements!"
        if "429" in err_msg: return "Error|0|Quota Exceeded"
        return "Error|0|System Fail"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

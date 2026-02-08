import os
import requests
import json
import traceback
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจต่างๆ จาก Render ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ตั้งค่า AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# โมเดลที่ใช้ (แนะนำ 1.5-flash เพราะเร็วและแม่นยำ)
MODEL_NAME = 'models/gemini-1.5-flash'

# --- 2. ฟังก์ชันส่ง LINE ---
def send_line_alert(text_message):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        print("LINE keys missing, skipping notification.")
        return

    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_TOKEN}'
    }
    
    data = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text_message}]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"LINE Sent: {response.status_code}")
    except Exception as e:
        print(f"LINE Error: {e}")

@app.route('/')
def home():
    return f"Sourdough Monitor & LINE Bot is Running! (Model: {MODEL_NAME})"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- New Request ---")
    
    # 1. รับรูปภาพจาก ESP32
    if 'imageFile' not in request.files:
        return "Error|0|No Image Sent"
    
    file = request.files['imageFile']
    
    # 2. เรียกใช้ Gemini
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        # Prompt สั่งงาน (ให้ตอบแบบฟอร์มเป๊ะๆ เพื่อเอาไปโชว์บนจอ ESP32)
        prompt = """
        Analyze this sourdough starter image.
        
        Strictly return ONE line in this format using pipe '|' separator:
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: Ready, Peak, Hungry, Moldy, Sleepy.
        TimeRemaining: integer minutes (put 0 if ready/bad).
        ShortAdvice: Very short advice (max 6 words).
        
        Example: Ready|0|Bake immediately!
        """
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": file.read()}
        ])
        
        # คลีนข้อมูลคำตอบ
        result_text = response.text.strip()
        result_text = result_text.replace('```', '').replace('\n', '')
        print(f"AI Says: {result_text}")

        # --- 3. ตรรกะการส่ง LINE ---
        # แยกชิ้นส่วนคำตอบ (เช่น "Ready|0|Bake now")
        parts = result_text.split('|')
        status = parts[0].strip() if len(parts) > 0 else ""
        advice = parts[2].strip() if len(parts) > 2 else ""

        # ส่งไลน์เฉพาะถ้า: พร้อม (Ready), พีค (Peak), หรือ ราขึ้น (Moldy)
        if "Ready" in status or "Peak" in status or "Moldy" in status:
            emoji = "🍞"
            if "Moldy" in status: emoji = "⚠️ อันตราย!"
            if "Ready" in status or "Peak" in status: emoji = "✅ น้องพร้อมแล้ว!"
            
            line_msg = f"{emoji}\nสถานะ: {status}\nคำแนะนำ: {advice}\n(รีบไปดูที่ตู้ด่วน!)"
            send_line_alert(line_msg)
        
        # ส่งค่ากลับไปให้ ESP32 โชว์บนหน้าจอ
        return result_text

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        # ส่ง Error กลับไปโชว์ที่จอ ESP32 แบบสั้นๆ
        if "404" in str(e): return "Error|0|Model Not Found"
        if "429" in str(e): return "Error|0|Quota Exceeded"
        return "Error|0|System Fail"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

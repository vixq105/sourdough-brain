import os
import requests
import json
import traceback
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# --- 1. ตั้งค่ากุญแจ (ดึงจาก Render Environment) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# ตั้งค่า AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ⚠️ ใช้ตัวนี้ครับ! มีมานานแล้ว รับรอง Server รู้จักแน่นอน
MODEL_NAME = 'gemini-pro'

# --- 2. ฟังก์ชันส่ง LINE (ส่งเฉพาะตอนสำคัญ) ---
def send_line_alert(message):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        print("LINE keys missing, skipping.")
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
    return f"Sourdough Monitor (Classic Model: {MODEL_NAME}) Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    print("--- New Request Incoming ---")
    
    # 1. รับรูปจาก ESP32
    if 'imageFile' not in request.files:
        return "Error|0|No Image Sent"
    
    file = request.files['imageFile']
    
    try:
        # 2. เรียกใช้ Gemini Pro (ตัวเสถียร)
        model = genai.GenerativeModel(MODEL_NAME)
        
        # คำสั่ง (Prompt) - ย้ำเรื่องรูปแบบคำตอบ
        prompt = """
        You are a Sourdough Expert. Analyze this image of a starter.
        
        STRICTLY return ONE line in this format using pipe '|' separator:
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: Ready, Peak, Hungry, Moldy, Sleepy.
        TimeRemaining: integer minutes (put 0 if ready/bad).
        ShortAdvice: Max 6 words.
        
        Example: Ready|0|Bake immediately!
        """
        
        # ส่งรูปภาพ
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": file.read()}
        ])
        
        # คลีนข้อมูลคำตอบ (ลบพวก markdown ที่ AI ชอบแถมมา)
        result_text = response.text.strip()
        result_text = result_text.replace('```', '').replace('*', '').replace('\n', '')
        
        print(f"AI Says: {result_text}")

        # --- 3. ตรรกะการส่ง LINE ---
        # ส่งไลน์ถ้าสถานะคือ: Ready, Peak, หรือ Moldy
        if any(status in result_text for status in ["Ready", "Peak", "Moldy"]):
            emoji = "🍞"
            if "Moldy" in result_text: emoji = "⚠️ อันตราย!"
            elif "Ready" in result_text or "Peak" in result_text: emoji = "✅ น้องฟูแล้ว!"
            
            # ตัดคำให้สวยงาม
            parts = result_text.split('|')
            status_show = parts[0] if len(parts) > 0 else result_text
            advice_show = parts[2] if len(parts) > 2 else ""
            
            line_msg = f"{emoji}\nสถานะ: {status_show}\nแนะนำ: {advice_show}\n(รีบไปดูที่ตู้ด่วน!)"
            send_line_alert(line_msg)
        
        # ส่งค่ากลับไปโชว์บนหน้าจอ ESP32
        return result_text

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        err_msg = str(e)
        
        # ดักจับ Error เพื่อบอก user ง่ายๆ
        if "404" in err_msg: return "Error|0|Model Not Found"
        if "429" in err_msg: return "Error|0|Quota Exceeded"
        
        return "Error|0|System Fail"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

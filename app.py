timport os
import requests
import json
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# --- 1. ดึงกุญแจจาก Render ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
LINE_USER_ID = os.environ.get("LINE_USER_ID")         # ส่งหาใคร (ID คุณ)
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN") # กุญแจบอท

# --- 2. ฟังก์ชันส่งไลน์ (Messaging API - Text Only) ---
def send_line_message(text_message):
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_TOKEN}'
    }
    
    # แพ็คข้อมูลใส่กล่อง JSON
    data = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": text_message
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"LINE Response: {response.status_code}") # 200 = สำเร็จ
    except Exception as e:
        print(f"Error sending LINE: {e}")

@app.route('/')
def home():
    return "Sourdough Monitor (Line Messaging API) is Running!"

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if 'imageFile' not in request.files:
        return "No image uploaded", 400

    file = request.files['imageFile']

    # --- 3. ให้ Gemini วิเคราะห์ ---
    try:
        # เปลี่ยนเป็น 'gemini-pro' เพื่อความชัวร์
        model = genai.GenerativeModel('gemini-pro') 
        
        prompt = """
        Analyze this sourdough starter image.
        Classify status strictly as one of: Ready, Peak, Hungry, Moldy, Sleepy.
        Return format: "Status: [Status] - [Short Advice]"
        Example: "Status: Ready - Perfect for baking!"
        """
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": file.read()}
        ])
        
        result_text = response.text.strip()
        print(f"AI Analysis: {result_text}")

        # --- 4. เงื่อนไขการส่งไลน์ ---
        # ส่งไลน์เฉพาะถ้า "พร้อมใช้" (Ready/Peak) หรือ "มีปัญหา" (Moldy)
        if "Ready" in result_text or "Peak" in result_text or "Moldy" in result_text:
            
            # แต่งข้อความให้น่ารัก
            emoji = "🍞"
            if "Moldy" in result_text: emoji = "⚠️ ตรวจพบเชื้อรา!"
            if "Ready" in result_text or "Peak" in result_text: emoji = "✅ น้องพร้อมแล้ว!"
            
            # ส่งข้อความเข้ามือถือคุณ
            msg = f"{emoji}\nผลวิเคราะห์: {result_text}\n(รีบไปดูที่ตู้ด่วน!)"
            send_line_message(msg)
            
        return result_text

    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)


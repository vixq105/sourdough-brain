import os
from flask import Flask, request
import google.generativeai as genai
from PIL import Image
import io
import base64

# =================ตั้งค่า API KEY ตรงนี้=================
# อย่าลืมใส่ API Key ของคุณในบรรทัดข้างล่างนี้นะครับ
GENAI_API_KEY = "AIzaSyCGk8FcySmCgnrteDdMdSHSWFPIErBvauM" 
# ====================================================

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Sourdough AI Brain is Running!"

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # 1. รับข้อมูลจาก ESP32
        image_data = request.form.get('image')
        temp = request.form.get('temp', '25')
        hum = request.form.get('hum', '60')

        if not image_data:
            return "Error|0|No Image Sent"

        # 2. แปลงภาพ Base64 เป็นรูปภาพจริง
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))

        # 3. สั่ง Gemini ให้วิเคราะห์
        prompt = f"""
        You are a sourdough expert. Analyze this image of a starter.
        Current Environment: Temperature {temp}°C, Humidity {hum}%.
        
        Strictly return the response in this format ONLY (use pipe '|' separator):
        Status|TimeRemaining(mins)|ShortAdvice

        Status options: 'Feeding Needed', 'Rising', 'Peak/Ready', 'Over-fermented', 'Moldy/Bad'.
        TimeRemaining: Estimate minutes until ready (put 0 if ready or bad).
        ShortAdvice: One short sentence advice.
        """
        
        response = model.generate_content([prompt, image])
        text_response = response.text.strip()
        
        # ลบ Markdown ออก
        text_response = text_response.replace('```', '').replace('python', '').strip()
        
        print(f"AI Says: {text_response}")
        return text_response

    except Exception as e:
        print(f"Error: {str(e)}")
        return f"System Error|0|{str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

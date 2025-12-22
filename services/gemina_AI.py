import requests
import os 
from dotenv import load_dotenv

load_dotenv()
#API_KEY = os.getenv("GEMINA_API_KEY")

# API URL

def get_company_description(stock_name):
    api_key = os.getenv("GEMINI_API_KEY")
    #print(api_key)
    if not api_key:
        raise EnvironmentError("กรุณาตรวจสอบ API Key ในไฟล์ .env หรือไม่ได้ส่งผ่านพารามิเตอร์")
    
    url = f"https://genarativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    prompt = f"""
    กรุณาอธิบายบริษัท {stock_name} ประกอบธุรกิจอะไร มีผลิตภัณฑ์หรือบริการอะไรบ้าง
    และมีจุดเด่นหรือความได้เปรียบทางการแข่งขันอย่างไร มีรายละเอียดอะไรที่สำคัญ เช่น
    รายได้หลัก สินค้ามีอะไรพัฒนาใหม่บ้าง จุดเด่น ขอให้ตอบเป็นภาษาไทย
    """
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}],
            }
        ]
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            return f" เกิดข้อผิดพลาดในการดึงข้อมูล: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Exception: {str(e)}"
    
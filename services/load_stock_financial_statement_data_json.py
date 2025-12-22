from financetoolkit import Toolkit
from dotenv import load_dotenv
import json, os, pandas as pd
import requests
from datetime import datetime
from collections import defaultdict


class FinancialsStatement():
    load_dotenv()
    def __init__(self, symbol=None): #API_KEY=None):

        self.api_key = os.getenv("API_KEY")
       
        if not self.api_key:
            raise EnvironmentError("\n กรุณาตรวจสอบ API Key ในไฟล์ .env หรือไม่ได้ส่งผ่านพารามิเตอร์")

        self.symbol = symbol.upper()
        self.file_path = f"data/{self.symbol}_financials.json"
        self.toolkit = Toolkit([self.symbol], api_key=self.api_key)
        self.basic_info = {}
        self.data = {}
    
    def load_data_json_or_api(self):
        """ โหลดไฟล์ข้อมูลงบการเงินจากไฟล์ JSON ถ้าไม่มีไห้ดึงไฟล์จาก API แล้วบันทึก """
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self.data = json.load(f)
                print(f" โหลดข้อมูลจากไฟล์สำเร็จ: {self.symbol}")
              # ✅ ถ้าไม่มี Basic Info → ดึงทันที
        else:
            print(f" ไม่พบไฟล์ {self.file_path} -> ดึงจาก API ....")
            #self.Load_basic_info
            self.Load_Financials_Statement_Stock_API()
            self.save_to_json()
            print(f"ดึงข้อมูลจาก API และบันทึกผลเรียบร้อย")

    def Load_Financials_Statement_Stock_API(self):
        #import requests

        print(f"🔄 กำลังโหลดข้อมูลการเงินของ {self.symbol}...")
        # ดึงงบการเงินจาก API FinancialToolkit
        income_statement = self.toolkit.get_income_statement()
        balance_sheet = self.toolkit.get_balance_sheet_statement()
        cash_flow_statement = self.toolkit.get_cash_flow_statement()

        if income_statement is None or balance_sheet is None or cash_flow_statement is None:
            print("❌ ดึงข้อมูลไม่สำเร็จ กรุณาตรวจสอบ API Key หรือ Symbol ที่กรอก")
            return None, None, None
    
        # ดึงราคาหุ้นจาก FMP API
        url = f"https://financialmodelingprep.com/api/v3/quote/{self.symbol}?apikey={self.api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            try:
                data = response.json()
                if not data:
                    raise ValueError(f" ไม่พบข้อมูลของหุ้น {self.symbol}")
         
            except Exception as e:
                print("โครงสร้างข้อมูลผิดราคาผิด:", e)
                #self.basic_info = {}
    
        url_hist = f"https://financialmodelingprep.com/api/v3/historical-price-full/{self.symbol}?serietype=line&timeseries=2000&apikey={self.api_key}"
        hist_response = requests.get(url_hist)
        prices_filterd = {}

        if hist_response.status_code == 200:
            hist_data = hist_response.json()
            historical = hist_data.get("historical", [])

            year_to_prices = {}
            for item in historical:
                date_str = item["date"]
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                year = date_obj.year
                if year not in year_to_prices:
                    year_to_prices[year] = []
                year_to_prices[year].append((date_obj, item["close"]))

            prices_by_year = {}
            for year, entries in year_to_prices.items():
                target = datetime(year, 12, 31)
                closest = min(entries, key=lambda x: abs((x[0] - target).days))
                prices_by_year[year] = round(closest[1], 2)

            try:
                available_years = set(income_statement.T.index.astype(str))
            except Exception as e:
                print("ไม่สามารถเข้าถึง Index ของ income statement")
                return None, None, None

            for year, price in prices_by_year.items():
                year_str = str(year)
                if year_str in available_years:
                    prices_filterd[year_str] = price
            
            self.basic_info = {
                    "symbol": self.symbol,
                    "name": data[0].get("name", ""),
                    "price": data[0].get("price", 0.0),
                    "marketCap": 0,
                    "prices": prices_filterd,
            }
            # สร้างโฟลเดอร์ data ถ้ายังไม่มี
            os.makedirs("data", exist_ok=True)
            # แปลงข้อมูลเป็น JSON
            #financial
            income_statement_data = json.loads(income_statement.T.to_json(orient="index"))
            # --- Merge basic info with financial data
            for year_str, price in prices_filterd.items():
            #    year_str = str(year)
                if year_str in income_statement_data:
                    income_statement_data[year_str]["price"] = price

            self.data = {
                "Basic Info": self.basic_info,
                "Income Statement": income_statement_data,
                #"Income Statement": json.loads(income_statement.T.to_json(orient="index")),
                "Balance Sheet": json.loads(balance_sheet.T.to_json(orient="index")),
                "Cash Flow Statement": json.loads(cash_flow_statement.T.to_json(orient="index"))

            }

    def save_to_json(self):
        # บันทึกข้อมูลลงไฟล์ JSON
        #filepath = f"data/{self.symbol}_financials.json"
        os.makedirs("data", exist_ok=True)
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=4)
            print(f" บันทึกข้อมูลสำเร็จที่ {self.file_path}")

        
    def get_combined_data(self):
        if not self.data:
            print(" self.data ยังว่าง")
            return None
        return {
            "Basic Info": self.data.get("Basic Info", {}),
            "Income Statement": self.data.get("Income Statement", {}),
            "Balance Sheet": self.data.get("Balance Sheet", {}),
            "Cash Flow Statement": self.data.get("Cash Flow Statement", {})
        }
    

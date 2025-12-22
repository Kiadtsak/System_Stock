import os
import pandas as pd
import numpy as np

EXPORT_PATH = "expotes/result.json"

def load_result_json(path=EXPORT_PATH):
    if not os.path.exists(path):
        raise FileExistsError(f"ไม่พบไฟล์: {path}")
    return pd.read_json(path)

def classify_industry(stock_symbol, df=None):
    # ถ้าไม่มี Sector ในไฟล์ result.json
    if df is not None and "Sector" in df.columns:
        sector = df[df["Stock Symbol"] == stock_symbol]["Sector"].iloc[0]
        return sector
    
    # ถ้าไม่มี Sector ให้ใช้ Mannual mapping
    tech = ["AAPL", "MSFT", "NVDA", "AMD", "GOOGL"]
    real_estate = ["CPN"]
    finance = ["KBANK", "SCB", "BBL"]    
     
    if stock_symbol.upper() in tech:
        return "Technology"
    elif stock_symbol.upper() in real_estate:
        return "Real Estate"
    elif stock_symbol.upper() in finance:
        return "Finance"
    return "Other"

def calculate_growth_rate(df, column="Owner Earnings"):
    df = df.sort_values("Year")
    df["YoY Growth (%)"] = df[column].pct_change() * 100
    return df

def valuation_dcf(df, fcf_col="Free Cash Flow (FCF)", wacc_col="WACC", growth_rate=0.05, years=5):
    latest_fcf = df[fcf_col].iloc[-1]
    wacc = df[wacc_col].iloc[-1]
    if wacc <= 0:
        raise ValueError("WACC ต้องมากกว่า 0")

    cashflows = [(latest_fcf * ((1 + growth_rate) ** i)) / ((1 + wacc) ** i) for i in range(1, years + 1)]
    terminal_value = (latest_fcf * (1 + growth_rate) ** years) * (1 + growth_rate) / (wacc - growth_rate)
    terminal_value_discounted = terminal_value / ((1 + wacc) ** years)

    return sum(cashflows) + terminal_value_discounted

def predict_future_price(df, intrinsic_value):
    shares_outstanding = df["Shares Outstanding"].iloc[-1]
    if shares_outstanding <= 0:
        raise ValueError("Shares Outstanding ต้องมากกว่า 0")
    return intrinsic_value / shares_outstanding

def run_valuation_analysis(symbol):
    df = load_result_json()
    stock_df = df[df["Stock Symbol"] == symbol]

    if stock_df.empty:
        raise ValueError(f"ไม่พบข้อมูลหุ้น {symbol} ในไฟล์ result.json")

    industry = classify_industry(symbol, df)
    stock_df = calculate_growth_rate(stock_df)

    intrinsic_value = valuation_dcf(stock_df)
    future_price = predict_future_price(stock_df, intrinsic_value)

    result = {
        "symbol": symbol,
        "industry": industry,
        "growth": stock_df[["Year", "YoY Growth (%)"]].to_dict(orient="records"),
        "intrinsic_value": intrinsic_value,
        "future_price": future_price
    }
    return result
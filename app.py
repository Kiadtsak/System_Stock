# app.py

import json
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "expotes" / "result.json"

from main import (
    load_financial_data, validate_data, calculate_ratios,
    export_ratios_to_file, parse_years, EXPORT_JSON
)
from Valuetion_model.valuetion_financials import run_valuation_for_symbol

app = FastAPI(title="Financials API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000", "http://127.0.0.1:5500",
        "http://localhost:5500", "http://localhost:3000"
        "http://AnalysisWindzora.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True, "v": "result-json-mode"}

# ------------------ helper: แปลง list(rows) -> ratios dict ------------------
def rows_to_ratios(rows: list[dict]) -> dict:
    out: dict = {}
    for r in rows:
        y = str(r.get("Year"))
        for k, v in r.items():
            if k in ("Year", "Stock Symbol", "symbol", "Symbol"):
                continue
            if k not in out:
                out[k] = {}
            out[k][y] = v
    return out

# ✅ endpoint หลัก: “ต้องประเมินก่อนทุกครั้ง” แล้วค่อยส่ง result.json
@app.get("/api/financials")
def financials(
    symbol: str = Query(...),
    years: str | None = None,
    refresh: bool = False
) -> Dict[str, Any]:
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=400, detail="Symbol is required")

    # 1) โหลดงบดิบ (จะ refresh หรือไม่แล้วแต่ param)
    data = load_financial_data(sym, force_refresh=refresh)
    income, balance, cashflow, basic = validate_data(data)

    # 2) คำนวณ ratio แล้ว export -> expotes/result.json
    ys = parse_years(years)
    ratios_by_year = calculate_ratios(income, balance, cashflow, basic, ys)
    export_ratios_to_file(sym, ratios_by_year)

    # 3) ประเมินมูลค่า (อ่านจาก expotes/result.json เป็นฐาน)
    valuation = None
    try:
        valuation = run_valuation_for_symbol(sym, export_json_path=EXPORT_JSON)
    except Exception as e:
        valuation = {"error": str(e)}

    # 4) อ่านผลลัพธ์ที่ “ประเมินแล้ว” จาก expotes/result.json
    if not RESULT_PATH.exists():
        raise HTTPException(status_code=500, detail="result.json not generated")

    try:
        all_rows = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read result.json failed: {e}")

    if not isinstance(all_rows, list):
        raise HTTPException(status_code=500, detail="result.json must be a list")

    rows = [
        r for r in all_rows
        if str(r.get("Stock Symbol") or r.get("symbol") or r.get("Symbol") or "").upper() == sym
    ]
    if not rows:
        raise HTTPException(status_code=404, detail=f"No rows for {sym} in result.json")

    # sort ปี
    def _year(x):
        try: return int(x.get("Year"))
        except: return 0
    rows = sorted(rows, key=_year)

    return {
        "symbol": sym,
        "source_file": str(RESULT_PATH),
        "result": rows,
        "latest": rows[-1],
        "years": [str(r.get("Year")) for r in rows],
        "ratios": rows_to_ratios(rows),     # ✅ ทำให้ app.js ใช้ ratio tabs ได้เลย
        "valuation": valuation              # ✅ ส่ง valuation ไปด้วย
    }

# (ทางเลือก) ถ้าอยากดูงบดิบจริง ๆ ให้แยก endpoint นี้ไว้
@app.get("/api/raw_financials")
def raw_financials(symbol: str) -> Dict[str, Any]:
    data = load_financial_data(symbol)
    income, balance, cashflow, basic = validate_data(data)
    return {
        "symbol": symbol.upper(),
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow_statement": cashflow,
        "basic_info": basic,
    }

# เสิร์ฟ frontend เหมือนเดิม
FE_DIR = ROOT / "frontend"
if FE_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FE_DIR), html=True), name="frontend")

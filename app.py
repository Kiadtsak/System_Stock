# app.py

import json
from pathlib import Path
from typing import Dict, Any
import time
import logging
import re

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from Blackend.AI.gpt_engine import GPTAnalysisEngine  

ROOT = Path(__file__).resolve().parent


from main import (
    load_financial_data, validate_data, calculate_ratios,
    export_ratios_to_file, parse_years, EXPORT_JSON
)
from Blackend.valuetion_financials import run_valuation_for_symbol

app = FastAPI(title="Financials API", version="1.0")


logger = logging.getLogger("AI")
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    #allow_origins=[
    #    "http://127.0.0.1:8000", 
    #    "http://127.0.0.1:5500",
    #    "http://localhost:5500", 
    #    "http://localhost:3000",
    #],
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
    
    # 4) อ่านผลลัพธ์ที่ “ประเมินแล้ว” จาก expotes/result.json
    export_ratios_to_file(sym, ratios_by_year)

    rows = []
    for year, values in ratios_by_year.items():
        row = {
            "symbol": sym,
            "Year": year,
            **values
        }
        rows.append(row)

    rows = sorted(rows, key=lambda x: int(x.get("Year", 0)))

    return {
        "symbol": sym,
        "result": rows,
        "latest": rows[-1] if rows else None,
        "years": [str(r.get("Year")) for r in rows],
        "ratios": rows_to_ratios(rows), 
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
import json
import re
import time
from typing import Any, Dict

from fastapi import HTTPException


def _extract_text_from_analysis(analysis: Any) -> str:
    """
    Accepts str/dict/list/other; returns the best-effort text content.
    """
    if analysis is None:
        return ""

    if isinstance(analysis, str):
        s = analysis.strip()
        # If it's JSON string, parse it
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                analysis = json.loads(s)
            except json.JSONDecodeError:
                return s
        else:
            return s

    if isinstance(analysis, dict):
        # common pattern: {"ผลการวิเคราะห์": "..."} or {"text": "..."}
        for k in ("ผลการวิเคราะห์", "text", "analysis", "content"):
            v = analysis.get(k)
            if isinstance(v, str) and v.strip():
                return v
        # fallback: stringify dict
        return json.dumps(analysis, ensure_ascii=False)

    if isinstance(analysis, list):
        return json.dumps(analysis, ensure_ascii=False)

    return str(analysis)


def _format_to_bullets(text: str) -> str:
    """
    Turns the AI text into readable numbered sections + bullet points (Markdown).
    """
    if not text:
        return ""

    # Convert escaped newlines if the text contains literal "\n"
    text = text.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]  # drop empty

    # Normalize bullets to "-"
    norm = []
    for ln in lines:
        ln = re.sub(r"^\s*[•●▪]+\s*", "- ", ln)
        ln = re.sub(r"^\s*-\s*", "- ", ln)
        norm.append(ln)

    # Group by headings like "### 1) ...."
    sections: list[tuple[str, list[str]]] = []
    current_title = "ผลการวิเคราะห์"
    current_items: list[str] = []

    heading_re = re.compile(r"^#{2,6}\s*(.+)$")
    numbered_heading_re = re.compile(r"^(?:#{0,6}\s*)?(\d+)\)\s*(.+)$")

    def flush():
        nonlocal current_title, current_items
        if current_items:
            sections.append((current_title, current_items))
        current_items = []

    for ln in norm:
        m1 = heading_re.match(ln)
        if m1:
            flush()
            title = m1.group(1).strip()
            # strip leading numbering inside heading if present
            mnum = numbered_heading_re.match(title)
            if mnum:
                title = f"{mnum.group(1)}) {mnum.group(2).strip()}"
            current_title = title
            continue

        # If line starts with "1) ...." without ###, treat as new section too
        m2 = numbered_heading_re.match(ln)
        if m2 and not ln.startswith("- "):
            flush()
            current_title = f"{m2.group(1)}) {m2.group(2).strip()}"
            continue

        # Make non-bullet lines into bullets (so it won't be one long paragraph)
        if not ln.startswith("- "):
            ln = f"- {ln}"
        current_items.append(ln)

    flush()

    # Render markdown: headings + bullets
    out: list[str] = []
    for title, items in sections:
        out.append(f"### {title}")
        out.extend(items)
        out.append("")  # spacing

    return "\n".join(out).strip()

from Blackend.AI.ai_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

@app.post("/api/ai-analysis")
def ai_analysis(payload: Dict[str, Any]):
    start = time.time()
    logger.info("🧠 AI analysis requested")

    # ---------- 1) Validate payload ----------
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be JSON object")

    result = payload.get("result")
    if not isinstance(result, list) or not result:
        raise HTTPException(
            status_code=400,
            detail="Payload must contain non-empty 'result' list",
        )

    # ---------- 2) Load base data ----------
    try:
        engine = GPTAnalysisEngine()
        analysis = engine.analyze_from_files(
            result=result,
            use_latest_only=False,
        )
    except Exception as e:
        logger.error("🔥 AI ENGINE FAILED")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "AI analysis failed",
                "error": str(e),
                "type": type(e).__name__,
            },
        )

    # ---------- 4) Done ----------
    elapsed = round(time.time() - start, 2)
    logger.info(f"✅ AI analysis completed in {elapsed}s")

    # ---------- 5) Beautify into bullet list, return as str ----------
    analysis = _extract_text_from_analysis(analysis)
    analysis = _format_to_bullets(analysis)
       
   
    return {
        "status": "success",
        "elapsed_seconds": elapsed,
        "analysis": {
            "text": analysis,  # ✅ เป็น str และแยกเป็นข้อแล้ว
        },
    }





# เสิร์ฟ frontend เหมือนเดิม
FE_DIR = ROOT / "frontend"
if FE_DIR.exists():
   app.mount("/", StaticFiles(directory=str(FE_DIR), html=True), name="frontend")

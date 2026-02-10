
#ai_engine.py

# Blackend/AI/gpt_engine.py


from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ai_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class GPTAnalysisEngine:
    def analyze_from_files(
        self,
        result: list,
        valuation_obj: dict | None = None,
        use_latest_only: bool = True,
        model: str = "gpt-4o",
    ) -> Dict[str, Any]:
       
        if not result:
            return{
                "Error": "No result data provided."
            }

        ratios_for_ai = result[-1] if use_latest_only else result

        prompt = USER_PROMPT_TEMPLATE.format(
            ratios=json.dumps(ratios_for_ai, ensure_ascii=False),
            valuation=json.dumps(valuation_obj or {}, ensure_ascii=False),
        )

        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            #max_tokens=150,
            # ✅ JSON mode: ให้ได้ JSON object แน่ขึ้น (ยังต้องสั่งใน prompt ด้วย)
            #response_format={"type": "json_object"},  # :contentReference[oaicite:1]{index=1}
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text = (resp.choices[0].message.content or "").strip()

        # --- strict JSON parse (พร้อม fallback แบบไม่ทำให้ระบบล้ม) ---
        try:
           analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = {
                "quality": text,
                "profitability_efficiency": "-",
                "valuation": "-",
                "risks": "-",
                "view": "-",
                "suitable_for": "-",
                "_note": "AI ตอบไม่เป็น JSON 100% (fallback เก็บเป็นข้อความ)",
            }
        return analysis

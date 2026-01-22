
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
        ratios_path: str = "expotes/result.json",
        valuation_path: str = "expotes/valuation.json",
        use_latest_only: bool = True,
        model: str = "gpt-5.2",
    ) -> Dict[str, Any]:
        # --- load ratios ---
        ratios_obj: Any = json.loads(Path(ratios_path).read_text(encoding="utf-8"))

        # result.json ของคุณเป็น list[dict] (orient="records")
        if isinstance(ratios_obj, list) and ratios_obj:
            ratios_for_ai = ratios_obj[-1] if use_latest_only else ratios_obj
        else:
            ratios_for_ai = ratios_obj

        # --- load valuation (optional) ---
        valuation_obj: Any = {}
        vp = Path(valuation_path)
        if vp.exists():
            valuation_obj = json.loads(vp.read_text(encoding="utf-8"))

        prompt = USER_PROMPT_TEMPLATE.format(
            ratios=json.dumps(ratios_for_ai, ensure_ascii=False),
            valuation=json.dumps(valuation_obj or {}, ensure_ascii=False),
        )

        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
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
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {
                "quality": text,
                "profitability_efficiency": "-",
                "valuation": "-",
                "risks": "-",
                "view": "-",
                "suitable_for": "-",
                "_note": "AI ตอบไม่เป็น JSON 100% (fallback เก็บเป็นข้อความ)",
            }

        return {
            "source": {
                "ratios_path": str(ratios_path),
                "valuation_path": str(valuation_path),
                "use_latest_only": use_latest_only,
                "model": model,
            },
            "analysis": data,
        }


"""
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

from .ai_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class GPTAnalysisEngine:
    def analysis(self, result, valuation=None):
        # ใช้เฉพาะปีล่าสุด ลด token + กัน error
        latest = result[-1] if isinstance(result, list) else result

        prompt = USER_PROMPT_TEMPLATE.format(
            result=json.dumps(latest, ensure_ascii=False),
            valuation=json.dumps(valuation or {}, ensure_ascii=False)
        )

        response = client.chat.completions.create(
            model="gpt-5.2",
            response_format={"type": "json"},  #🔥 ขอ GPT ส่ง JSON มาเลย
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        text = response.choices[0].message.content.strip()
    
        # 🔥 บังคับให้ GPT ส่ง JSON เท่านั้น
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # fallback กันพัง
            return {
                "quality": text,
                "valuation": "-",
                "risk": "-",
                "view": "-"
            }
"""


"""
from openai import OpenAI
from .ai_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from dotenv import load_dotenv
import os


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

class GPTAnalysisEngine:
    def analysis(self, result, valuation):
        prompt = USER_PROMPT_TEMPLATE.format(result, valuation)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "uese", "content": prompt}
            ],
            temperature=0.2
        )

        return response.choices[0].message.content
"""
import json
import re

from google import genai
from src.config import settings
from src.prompts import build_analysis_prompt


class DataAgent:

    def __init__(self):

        self.gemini_client = None

        # Gemini
        if settings.GEMINI_API_KEY:
            self.gemini_client = genai.Client(
                api_key=settings.GEMINI_API_KEY
            )

    def _ask_gemini(self, prompt: str) -> str:

        if not self.gemini_client:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        response = self.gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )

        return response.text

    def _ask_model(self, prompt: str) -> str:

        if self.gemini_client:
            return self._ask_gemini(prompt)

        raise RuntimeError(
            "No working AI model is configured."
        )

    def _extract_json(self, text: str) -> dict:

        text = text.strip()

        text = re.sub(
            r"^```json\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"^```\s*",
            "",
            text,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:
            return json.loads(text)

        except json.JSONDecodeError:

            match = re.search(
                r"\{.*\}",
                text,
                flags=re.DOTALL,
            )

            if not match:
                raise ValueError(
                    "AI did not return valid JSON."
                )

            return json.loads(
                match.group()
            )

    def create_analysis(
        self,
        question: str,
        schema: dict,
        preview: list,
    ) -> dict:

        prompt = build_analysis_prompt(
            question=question,
            schema=schema,
            preview=preview,
        )

        response = self._ask_model(
            prompt
        )

        return self._extract_json(
            response
        )

    def explain_result(
        self,
        question: str,
        analysis: dict,
        result: str,
    ) -> str:

        prompt = f"""
You are a data analysis assistant.

The user asked:

{question}

The analysis operation was:

{analysis}

Python/Pandas calculated this actual result:

{result}

Explain the answer clearly.

Rules:
1. Use only the calculated result.
2. Never invent numbers.
3. Do not make assumptions.
4. Give the answer directly.
5. Briefly explain the calculation.
"""

        return self._ask_model(
            prompt
        )
import httpx
from typing import List

from .config import RAGSettings
from .store import SearchHit


class LLMClient:
    def __init__(self, settings: RAGSettings) -> None:
        self.settings = settings

    async def generate(self, question: str, hits: List[SearchHit]) -> tuple[str, bool]:
        if not self.settings.llm_api_base or not self.settings.llm_api_key:
            return self._fallback_answer(question, hits), False

        url = self._chat_url(self.settings.llm_api_base)
        system_prompt = (
            "You are a concise assistant. Use only the provided context. "
            "If the answer is not present, say you do not have enough context. "
            "Cite sources as [source:doc_id]."
        )
        context_block = self._format_context(hits)
        user_prompt = f"Question: {question}\n\nContext:\n{context_block}"

        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            return self._fallback_answer(question, hits), False
        return content, True

    def _chat_url(self, base: str) -> str:
        cleaned = base.rstrip("/")
        if cleaned.endswith("/chat/completions"):
            return cleaned
        if cleaned.endswith("/v1"):
            return f"{cleaned}/chat/completions"
        return f"{cleaned}/v1/chat/completions"

    def _format_context(self, hits: List[SearchHit]) -> str:
        parts = []
        for hit in hits:
            snippet = hit.text.strip().replace("\n", " ")
            parts.append(f"[{hit.doc_id}] {snippet}")
        return "\n".join(parts)

    def _fallback_answer(self, question: str, hits: List[SearchHit]) -> str:
        if not hits:
            return "No relevant context found to answer the question."
        bullet_points = "\n".join([f"- {hit.text[:240].strip()}" for hit in hits])
        return (
            "LLM provider not configured. Returning top matching passages:\n"
            f"{bullet_points}"
        )
"""Client du modèle de langage : Ollama (Qwen3.5-4B en local) ou une API
compatible OpenAI (Cerebras). Les deux renvoient le même format :

    {"content": str, "tool_calls": [{"id": str, "name": str, "arguments": dict}],
     "usage": {"prompt_tokens": int, "completion_tokens": int}}
"""
from __future__ import annotations

import json
import os

import requests

from analyst import config


def _parse_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {"_invalid_json": raw}


class OllamaLLM:
    def __init__(self, model: str = config.MODEL, url: str = config.OLLAMA_URL,
                 num_ctx: int = config.NUM_CTX, temperature: float = config.TEMPERATURE,
                 think: bool = config.THINK):
        self.model, self.url, self.num_ctx = model, url.rstrip("/"), num_ctx
        self.temperature, self.think = temperature, think

    @staticmethod
    def _to_ollama(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            m2 = {"role": m["role"], "content": m.get("content") or ""}
            if m.get("tool_calls"):
                m2["tool_calls"] = [{"function": {"name": c["name"], "arguments": c["arguments"]}}
                                    for c in m["tool_calls"]]
            if m["role"] == "tool":
                m2["tool_name"] = m.get("name", "")
            out.append(m2)
        return out

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        body = {"model": self.model, "messages": self._to_ollama(messages), "stream": False,
                "think": self.think,
                "options": {"num_ctx": self.num_ctx, "temperature": self.temperature}}
        if tools:
            body["tools"] = tools
        r = requests.post(f"{self.url}/api/chat", json=body, timeout=600)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        calls = [{"id": f"call_{i}", "name": c["function"]["name"],
                  "arguments": _parse_args(c["function"].get("arguments"))}
                 for i, c in enumerate(msg.get("tool_calls") or [])]
        return {"content": msg.get("content") or "", "tool_calls": calls,
                "usage": {"prompt_tokens": data.get("prompt_eval_count", 0),
                          "completion_tokens": data.get("eval_count", 0)}}


class OpenAICompatLLM:
    """Pour Cerebras (qwen-3.8-27b) si l'ordinateur ne fait pas tourner le 4B."""

    def __init__(self, model: str = config.MODEL, base_url: str = config.OPENAI_BASE_URL,
                 api_key_env: str = config.API_KEY_ENV, temperature: float = config.TEMPERATURE):
        key = os.environ.get(api_key_env)
        if not key:
            raise RuntimeError(f"variable d'environnement {api_key_env} absente")
        self.model, self.base_url, self.key = model, base_url.rstrip("/"), key
        self.temperature = temperature

    @staticmethod
    def _to_openai(messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            m2 = {"role": m["role"], "content": m.get("content") or ""}
            if m.get("tool_calls"):
                m2["tool_calls"] = [{"id": c["id"], "type": "function",
                                     "function": {"name": c["name"],
                                                  "arguments": json.dumps(c["arguments"])}}
                                    for c in m["tool_calls"]]
            if m["role"] == "tool":
                m2["tool_call_id"] = m.get("tool_call_id", "")
            out.append(m2)
        return out

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        body = {"model": self.model, "messages": self._to_openai(messages),
                "temperature": self.temperature}
        if tools:
            body["tools"] = tools
        r = requests.post(f"{self.base_url}/chat/completions", json=body, timeout=600,
                          headers={"Authorization": f"Bearer {self.key}"})
        r.raise_for_status()
        data = r.json()
        msg = data["choices"][0]["message"]
        calls = [{"id": c.get("id", f"call_{i}"), "name": c["function"]["name"],
                  "arguments": _parse_args(c["function"].get("arguments"))}
                 for i, c in enumerate(msg.get("tool_calls") or [])]
        u = data.get("usage", {})
        return {"content": msg.get("content") or "", "tool_calls": calls,
                "usage": {"prompt_tokens": u.get("prompt_tokens", 0),
                          "completion_tokens": u.get("completion_tokens", 0)}}


def make_llm():
    if config.BACKEND == "openai":
        return OpenAICompatLLM()
    return OllamaLLM()

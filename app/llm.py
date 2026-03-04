"""LLM provider abstraction – supports Gemini (free), Groq (free), and Ollama (local)."""

from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_PROVIDER,
    OLLAMA_MODEL,
    OLLAMA_URL,
)

log = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Pull the first JSON object/array out of an LLM response that may contain markdown fences."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return m.group(1).strip()
    return text.strip()


async def call_llm(prompt: str, *, system: str = "", expect_json: bool = True) -> str:
    provider = LLM_PROVIDER.lower()
    if provider == "gemini":
        return await _call_gemini(prompt, system=system)
    if provider == "groq":
        return await _call_groq(prompt, system=system)
    if provider == "ollama":
        return await _call_ollama(prompt, system=system)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


async def call_llm_json(prompt: str, *, system: str = "") -> dict:
    raw = await call_llm(prompt, system=system, expect_json=True)
    cleaned = _extract_json(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        log.error("Failed to parse LLM JSON response:\n%s", raw[:500])
        raise


# ── Gemini (Google AI Studio – free tier) ────────────────────────────────────

async def _call_gemini(prompt: str, *, system: str = "") -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}"
        f":generateContent?key={GEMINI_API_KEY}"
    )
    parts = []
    if system:
        parts.append({"text": system + "\n\n"})
    parts.append({"text": prompt})

    payload = {"contents": [{"parts": parts}]}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Groq (free tier) ─────────────────────────────────────────────────────────

async def _call_groq(prompt: str, *, system: str = "") -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.2}
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"]


# ── Ollama (local) ────────────────────────────────────────────────────────────

async def _call_ollama(prompt: str, *, system: str = "") -> str:
    url = f"{OLLAMA_URL}/api/generate"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "system": system, "stream": False}
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return data["response"]

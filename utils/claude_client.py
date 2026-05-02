"""
OpenAI API client — drop-in replacement for the former Claude client.
All function signatures are identical so no pipeline code changes are needed.
Uses gpt-4o-mini for fast synthesis/extraction, gpt-4o for outreach writing.
"""
import structlog
from typing import Optional
from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MODEL_FULL

log = structlog.get_logger()

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def synthesise(
    system_prompt: str,
    user_data: str,
    model: str = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> Optional[str]:
    """
    Core synthesis call. Sends structured data to OpenAI and returns text output.
    Drop-in replacement for the former Claude synthesise() function.
    """
    if model is None:
        model = OPENAI_MODEL
    try:
        response = _get_client().chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_data},
            ],
        )
        result = response.choices[0].message.content
        log.info("openai_ok", model=model, tokens=response.usage.completion_tokens)
        return result
    except Exception as e:
        log.error("openai_error", error=str(e), model=model)
        return None


def classify(text: str, categories: list, context: str = "") -> Optional[str]:
    """Fast classification — returns one of the provided categories."""
    category_list = " | ".join(categories)
    prompt = f"""Classify the following text into exactly one category.
Categories: {category_list}
{f'Context: {context}' if context else ''}
Return ONLY the category name, nothing else."""

    result = synthesise(prompt, text, max_tokens=50, temperature=0)
    if result:
        result = result.strip()
        for cat in categories:
            if cat.lower() in result.lower():
                return cat
    return categories[-1]


def extract_json(
    system: str = "",
    user: str = "",
    instruction: str = "",
    data: str = "",
    schema_hint: str = "",
    model: str = None,
) -> Optional[dict]:
    """
    Extract structured JSON from unstructured text.
    Accepts either (system, user) or (instruction, data) kwargs.
    Returns parsed dict, or None on failure.
    """
    if model is None:
        model = OPENAI_MODEL
    sys_prompt = system or f"""You are a precise data extraction engine.
Extract information from the provided text and return ONLY valid JSON.
{f'Expected JSON structure: {schema_hint}' if schema_hint else ''}
Rules:
- Return ONLY JSON, no explanation
- Use null for missing fields
- Do not fabricate data
- Keep text values under 200 characters"""
    user_msg = user or (f"{instruction}\n\nData:\n{data}" if instruction else data)

    raw = synthesise(sys_prompt, user_msg, model=model, max_tokens=1500, temperature=0)
    if not raw:
        return None
    from utils.helpers import safe_json_parse
    return safe_json_parse(raw)


def extract_json_str(
    instruction: str,
    data: str,
    schema_hint: str = "",
) -> Optional[str]:
    """
    Extract structured JSON from unstructured text.
    Returns JSON string — caller is responsible for parsing.
    """
    system = f"""You are a precise data extraction engine.
Extract information from the provided text and return ONLY valid JSON.
{f'Expected JSON structure: {schema_hint}' if schema_hint else ''}
Rules:
- Return ONLY JSON, no explanation
- Use null for missing fields
- Do not fabricate data
- Keep text values under 200 characters"""

    return synthesise(system, f"{instruction}\n\nData:\n{data}")

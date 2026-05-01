"""
Claude API client — handles all LLM calls across the system.
Uses Haiku for fast classification/extraction, Sonnet for outreach writing.
"""
import anthropic
import structlog
from typing import Optional
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MODEL_FULL

log = structlog.get_logger()

# Lazy-initialise the client so imports never fail when no key is set.
# The client is created on first use inside each function.
_client: Optional["anthropic.Anthropic"] = None

def _get_client() -> "anthropic.Anthropic":
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def synthesise(
    system_prompt: str,
    user_data: str,
    model: str = CLAUDE_MODEL,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> Optional[str]:
    """
    Core synthesis call. Sends structured data to Claude and returns text output.

    Args:
        system_prompt: Role + instructions for the synthesis task
        user_data:     Pre-structured data from Layer 2 extraction
        model:         Which Claude model to use
        max_tokens:    Max output tokens
        temperature:   Lower = more deterministic (0.3 is good for analysis)

    Returns:
        Synthesised text string, or None on failure
    """
    try:
        response = _get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_data}]
        )
        result = response.content[0].text
        log.info("claude_synthesis_ok", model=model, tokens=response.usage.output_tokens)
        return result
    except anthropic.AuthenticationError:
        log.error("claude_auth_error", hint="Check ANTHROPIC_API_KEY in .env")
        return None
    except anthropic.RateLimitError:
        log.error("claude_rate_limit")
        return None
    except Exception as e:
        log.error("claude_error", error=str(e))
        return None


def classify(text: str, categories: list[str], context: str = "") -> Optional[str]:
    """
    Fast classification — returns one of the provided categories.
    Used for: business model type, sentiment, brand maturity score, etc.
    """
    category_list = " | ".join(categories)
    prompt = f"""Classify the following text into exactly one category.
Categories: {category_list}
{f'Context: {context}' if context else ''}
Return ONLY the category name, nothing else."""

    result = synthesise(prompt, text, max_tokens=50, temperature=0)
    if result:
        # Find closest match
        result = result.strip()
        for cat in categories:
            if cat.lower() in result.lower():
                return cat
    return categories[-1]   # Default to last category


def extract_json(
    system: str = "",
    user: str = "",
    instruction: str = "",
    data: str = "",
    schema_hint: str = "",
    model: str = CLAUDE_MODEL,
) -> Optional[dict]:
    """
    Extract structured JSON from unstructured text.
    Accepts either (system, user) or (instruction, data) kwargs.
    Returns parsed dict, or None on failure.
    """
    # normalise args — support both call styles
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

    return synthesise(system, f"{
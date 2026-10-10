
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str | None
    timeout_seconds: float
    max_retries: int
    max_output_tokens: int


def load_settings() -> LLMSettings:
    load_dotenv()

    provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()

    if provider not in {"mock", "gemini"}:
        raise ValueError(
            "LLM_PROVIDER must be either 'mock' or 'gemini'."
        )

    timeout_seconds = float(
        os.getenv("GEMINI_TIMEOUT_SECONDS", "30")
    )
    max_retries = int(
        os.getenv("GEMINI_MAX_RETRIES", "2")
    )
    max_output_tokens = int(
        os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1500")
    )

    if timeout_seconds <= 0:
        raise ValueError("GEMINI_TIMEOUT_SECONDS must be positive.")

    if max_retries < 0:
        raise ValueError("GEMINI_MAX_RETRIES cannot be negative.")

    if max_output_tokens <= 0:
        raise ValueError(
            "GEMINI_MAX_OUTPUT_TOKENS must be positive."
        )

    return LLMSettings(
        provider=provider,
        model=os.getenv(
            "GEMINI_MODEL", "gemini-2.5-flash-lite"
        ).strip(),
        api_key=os.getenv("GEMINI_API_KEY") or None,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_output_tokens=max_output_tokens,
    )

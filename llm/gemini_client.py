from google import genai
from google.genai import errors, types

from llm.config import LLMSettings, load_settings


class GeminiModelClient:
    def __init__(
        self,
        settings: LLMSettings | None = None,
        client=None,
    ):
        self.settings = settings or load_settings()

        if self.settings.provider != "gemini":
            raise ValueError(
                "GeminiModelClient requires LLM_PROVIDER=gemini."
            )

        if not self.settings.model:
            raise ValueError("GEMINI_MODEL cannot be empty.")

        if client is None and not self.settings.api_key:
            raise ValueError(
                "GEMINI_API_KEY is required for Gemini mode."
            )

        self._client = client or genai.Client(
            api_key=self.settings.api_key,
            http_options=types.HttpOptions(
                timeout=int(self.settings.timeout_seconds * 1000)
            ),
        )

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        if not system_prompt.strip():
            raise ValueError("system_prompt cannot be empty.")

        if not user_prompt.strip():
            raise ValueError("user_prompt cannot be empty.")

        try:
            response = await self._client.aio.models.generate_content(
                model=self.settings.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=self.settings.max_output_tokens,
                ),
            )

        except errors.APIError as exc:
            code = getattr(exc, "code", None)

            if code in {408, 409, 429} or (
                isinstance(code, int) and code >= 500
            ):
                raise ConnectionError(
                    f"Temporary Gemini API failure: {code}"
                ) from exc

            raise ValueError(
                f"Gemini API rejected the request: {code}"
            ) from exc

        except (TimeoutError, ConnectionError):
            raise

        text = (response.text or "").strip()

        if not text:
            raise ValueError(
                "Gemini returned an empty text response."
            )

        return text

    async def close(self):
        await self._client.aio.aclose()

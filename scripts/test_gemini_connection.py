
import asyncio

from llm.config import load_settings
from llm.gemini_client import GeminiModelClient


async def main():
    settings = load_settings()

    if settings.provider != "gemini":
        raise ValueError(
            "Set LLM_PROVIDER=gemini in your project-root .env file."
        )

    client = GeminiModelClient(settings)

    try:
        print(f"Testing Gemini model: {settings.model}")

        response = await client.generate_text(
            system_prompt=(
                "You are an engineering assistant. "
                "Answer briefly and clearly."
            ),
            user_prompt=(
                "List three essential components of a URL shortener."
            ),
        )

        print("\nGemini response:")
        print(response)
        print("\nGemini connection test passed!")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

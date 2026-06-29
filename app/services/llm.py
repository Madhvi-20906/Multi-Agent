import logging
from typing import List
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Single global client instance
_async_client: AsyncOpenAI = None

def get_openai_client() -> AsyncOpenAI:
    """
    Returns the global AsyncOpenAI client initialized with settings.
    """
    global _async_client
    if _async_client is not None:
        return _async_client
        
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY is not configured in settings!")
        
    client_kwargs = {"api_key": settings.OPENAI_API_KEY}
    if settings.OPENAI_BASE_URL:
        logger.info(f"Using custom OpenAI Base URL: {settings.OPENAI_BASE_URL}")
        client_kwargs["base_url"] = settings.OPENAI_BASE_URL

    _async_client = AsyncOpenAI(**client_kwargs)
    return _async_client

async def get_embedding(text: str) -> List[float]:
    """
    Generates 1536-dimensional vector embedding using OpenAI text-embedding-3-small.
    """
    client = get_openai_client()
    try:
        response = await client.embeddings.create(
            input=[text.replace("\n", " ")],
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding via OpenAI: {e}")
        # Return fallback zero vector of correct dimensions so process doesn't fail
        return [0.0] * 1536

def init_llm_services():
    """
    Diagnostic initializer to ensure API key presence.
    """
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is missing! Direct AI calls will fail.")
    else:
        logger.info("OpenAI LLM and Embedding Services ready.")

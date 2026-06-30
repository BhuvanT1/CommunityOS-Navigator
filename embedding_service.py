from google import genai
import numpy as np
from app.core.config import settings
from app.core.logging import logger

if settings.GEMINI_API_KEY:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
else:
    client = None

async def generate_embedding(text: str) -> list[float]:
    """
    Generates a 768-dimensional text embedding using Gemini 3.1 embedding model.
    """
    try:
        if not client:
            raise PermissionError("GEMINI_API_KEY is not configured")
            
        # text-embedding-004 is the recommended model for general text embeddings
        result = await client.aio.models.embed_content(
            model="text-embedding-004",
            contents=text,
            config=genai.types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        # Return zero vector fallback to prevent complete crash
        return [0.0] * 768

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calculates the cosine similarity between two vectors.
    Returns a float between -1.0 and 1.0 (1.0 = identical).
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
        
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
        
    return float(dot_product / (norm_v1 * norm_v2))

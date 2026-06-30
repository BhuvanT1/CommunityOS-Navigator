import json
import time
import io
import PIL.Image
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging import logger
from app.schemas.intake import AIAnalysisResult
from google import genai
from google.genai import types

import os

if settings.GEMINI_API_KEY:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
else:
    raise RuntimeError("Missing GEMINI_API_KEY")

AI_MODEL_VERSION = settings.GEMINI_MODEL
PROMPT_VERSION = "v1.0.0"
SCHEMA_VERSION = "v1.0.0"

PROMPT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "vision_prompt_v1.md")
with open(PROMPT_FILE, "r") as f:
    SYSTEM_PROMPT = f.read()

async def analyze_image_with_gemini(image_bytes: bytes) -> tuple[AIAnalysisResult, float, dict, str, dict]:
    logger.info("Starting Gemini Vision analysis")
    start_time = time.time()
    
    try:
        image = PIL.Image.open(io.BytesIO(image_bytes))
        
        if not client:
            raise PermissionError("GEMINI_API_KEY is not configured")
            
        from app.services.firestore_client import firestore_client
        app_settings = firestore_client.get_settings()
        
        # Determine Temperature based on strictness
        strictness = app_settings.get("strictness_level", "High")
        temperature = 0.1
        if strictness == "Low":
            temperature = 0.7
        elif strictness == "Medium":
            temperature = 0.4
        elif strictness == "High":
            temperature = 0.1
        elif strictness == "Max":
            temperature = 0.0
            
        max_tokens = int(app_settings.get("max_tokens", 2048))
        
        # Async call to Gemini SDK
        try:
            response = await client.aio.models.generate_content(
                model=AI_MODEL_VERSION,
                contents=[SYSTEM_PROMPT, image],
                config=types.GenerateContentConfig(
                    temperature=temperature, 
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                    response_schema=AIAnalysisResult
                )
            )
        except AttributeError:
            # Fallback if async not available
            response = client.models.generate_content(
                model=AI_MODEL_VERSION,
                contents=[SYSTEM_PROMPT, image],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                    response_schema=AIAnalysisResult
                )
            )
            
        gemini_latency = (time.time() - start_time) * 1000
        logger.info(f"Gemini API returned in {gemini_latency:.2f}ms")
        
        response_text = response.text.strip()
        
        # Defensively strip markdown if Gemini ignores instructions
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
            
        data = json.loads(response_text)
        result = AIAnalysisResult(**data)
        
        versions = {
            "gemini_version": AI_MODEL_VERSION,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "timestamp": int(time.time() * 1000)
        }
        
        input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
        output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
        
        # Gemini 3.1 Pro pricing
        input_cost = (input_tokens / 1_000_000) * 3.50
        output_cost = (output_tokens / 1_000_000) * 10.50
        estimated_cost = input_cost + output_cost

        metrics = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": round(estimated_cost, 6)
        }
        
        return result, gemini_latency, versions, response_text, metrics
        
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned malformed JSON: {str(e)}")
        raise ValueError("AI failed to generate a valid structured response.")
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Gemini API Failure: {error_msg}")
        
        if "timeout" in error_msg or "deadline" in error_msg:
            raise TimeoutError("The AI analysis timed out.")
        if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
            raise PermissionError("AI Rate limits exceeded. Please try again later.")
            
        raise RuntimeError(f"AI Service Error: {str(e)}")

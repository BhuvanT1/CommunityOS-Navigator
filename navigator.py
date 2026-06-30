from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.navigator_service import navigator_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class NavigatorRequest(BaseModel):
    query: str

@router.post("/ask")
async def ask_navigator(request: NavigatorRequest):
    try:
        response = navigator_service.process_query(request.query)
        return response
    except Exception as e:
        logger.error(f"Error processing navigator query: {e}")
        raise HTTPException(status_code=500, detail="Failed to process query through Navigator")

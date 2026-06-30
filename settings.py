from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.services.firestore_client import firestore_client
from app.models.response import APIResponse
from app.core.logging import logger

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingsPayload(BaseModel):
    settings: Dict[str, Any]

@router.get("", response_model=APIResponse[Dict[str, Any]])
async def get_settings():
    try:
        settings_data = firestore_client.get_settings()
        return APIResponse.success_response(data=settings_data)
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=APIResponse[Dict[str, Any]])
async def update_settings(payload: SettingsPayload):
    try:
        updated_data = firestore_client.update_settings(payload.settings)
        return APIResponse.success_response(data=updated_data)
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

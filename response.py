from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel
from app.core.logging import request_id_ctx_var

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[str] = None
    request_id: Optional[str] = None
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "Success"):
        req_id = request_id_ctx_var.get()
        return cls(success=True, message=message, data=data, request_id=req_id)
        
    @classmethod
    def error_response(cls, error: str, message: str = "An error occurred"):
        req_id = request_id_ctx_var.get()
        return cls(success=False, message=message, error=error, request_id=req_id)

import logging
import sys
from contextvars import ContextVar

# Context variable to store the request ID for the current async task
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default=None)

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        req_id = request_id_ctx_var.get()
        record.request_id = req_id if req_id else "SYSTEM"
        return True

def setup_logging():
    logger = logging.getLogger("community_os")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Format: [TIMESTAMP] [LEVEL] [REQ_ID] MESSAGE
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | req_id=%(request_id)-36s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        
        logger.addHandler(handler)
    
    # Silence excessive Uvicorn logs to let our custom logger shine
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    return logger

# Singleton logger instance to be imported across the app
logger = setup_logging()

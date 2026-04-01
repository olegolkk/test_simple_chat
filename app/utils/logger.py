import logging
from app.config import settings

def setup_logger(name: str = __name__) -> logging.Logger:
    """Настройка логгера"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(name)

logger = setup_logger(__name__)
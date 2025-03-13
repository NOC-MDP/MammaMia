# logger_config.py
import sys
from loguru import logger

# Define the custom log level only once
COMPLETED_LEVEL = 25
logger.level("COMPLETED", COMPLETED_LEVEL, color="<green>")

# Apply a default log filter to include specific levels
def log_filter(record):
    return record["level"].name in {"WARNING", "ERROR", "CRITICAL", "COMPLETED"}

# Configure the logger
logger.remove()
logger.add(sys.stderr, level="DEBUG", filter=log_filter)

# Export the logger
__all__ = ["logger", "COMPLETED_LEVEL"]

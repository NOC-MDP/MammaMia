# Copyright 2025 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from loguru import logger

# Define the custom log level only once
COMPLETED_LEVEL = 25
logger.level("COMPLETED", COMPLETED_LEVEL, color="<green>")

# Apply a default log filter to include specific levels
def log_filter(record):
    return record["level"].name in {"WARNING", "ERROR", "CRITICAL", "COMPLETED","SUCCESS"}

# Configure the logger
logger.remove()
logger.add(sys.stderr, level="DEBUG", filter=log_filter)

# Export the logger
__all__ = ["logger", "COMPLETED_LEVEL","log_filter"]

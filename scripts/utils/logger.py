import logging
from pathlib import Path
import os

if os.environ.get("APP_ENV") == "testing":
    log_file = "errors_testing.log"
else:
    log_file = "errors.log"

if os.environ.get("BASE_DIR"):
    log_path = Path(os.environ.get("BASE_DIR"), "logs", log_file)
else:
    log_path = Path(Path(__file__).parent.parent.parent, "logs", log_file)
date_format = "%Y-%m-%d %I:%M:%S %p"

# log to console
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)
c_format = logging.Formatter("[%(levelname)s] %(message)s", date_format)
c_handler.setFormatter(c_format)

# log to file
f_handler = logging.FileHandler(log_path)
f_handler.setLevel(logging.DEBUG)
f_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", date_format)
f_handler.setFormatter(f_format)

# log to console
preview_handler = logging.StreamHandler()
preview_handler.setLevel(logging.DEBUG)
preview_format = logging.Formatter("\n[CONSOLE]\n%(message)s")
preview_handler.setFormatter(preview_format)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(c_handler)
logger.addHandler(f_handler)

console = logging.getLogger("console")
console.setLevel(logging.DEBUG)
console.addHandler(preview_handler)

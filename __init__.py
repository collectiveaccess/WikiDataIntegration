from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

from .scripts.utils.wiki_queries import (
    search_keyword,
    fetch_and_format_all_properties,
    fetch_and_format_external_id_properties,
)
from .scripts.utils.wikidata_utils import *
from .scripts.utils.logger import logger

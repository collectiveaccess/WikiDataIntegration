from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

from .scripts.utils.wiki_queries import (
    search_keyword,
    fetch_and_format_all_properties,
    fetch_and_format_external_id_properties,
    fetch_and_format_labels_for_ids_sqarql,
    fetch_and_format_labels_for_ids
)
from .scripts.utils.wikidata_utils import *
from .scripts.utils.logger import logger
from .scripts.utils.wiki_serialization import get_claim_label
from .scripts.utils.import_wikidata_records import import_wikidata_item_to_local_wikibase

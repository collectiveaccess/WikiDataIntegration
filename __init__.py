from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

from .scripts.utils.wiki_queries import (
    search_keyword,
    fetch_and_format_all_properties,
    fetch_and_format_external_id_properties,
    fetch_and_format_labels_for_ids_sqarql,
    fetch_and_format_labels_for_ids,
    fetch_commons_media_metadata,
    format_commons_media_metadata_results
)
from .scripts.utils.wikidata_utils import *
from .scripts.utils.logger import logger
from .scripts.utils.wiki_serialization import get_claim_label
from .scripts.utils.import_wikidata_records import (
    find_or_create_local_item,
    add_statements_to_local_item,
    add_sources_and_qualifiers_to_local_item,
    import_wikidata_item_to_local_wikibase,
    create_local_id_label_dictionary
)

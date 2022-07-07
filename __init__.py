from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))

from .scripts.utils.wiki_queries import *
from .scripts.utils.wiki_serialization import *
from .scripts.utils.wikidata_utils import *

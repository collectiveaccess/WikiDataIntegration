import sys
from pathlib import Path
from datetime import date
from os.path import exists
import json
import os

import utils.wiki_queries as wq

project_path = Path(__file__).resolve().parent.parent
sys.path.append(str(project_path))

today = date.today()
filepath = project_path / "data" / f"wikdata_labels_{today}.json"

# if file exists, do nothing
if exists(filepath):
    print("wikidata.org labels were not updated.")
# if file does not exist, delete old files, get properties, create new file
else:
    for path in Path(project_path / "data").glob("wikdata_labels*.json"):
        os.remove(path)

    properties = wq.fetch_all_wikidata_properties()
    with open(filepath, "w") as outfile:
        json_object = json.dumps(properties, indent=2)
        outfile.write(json_object)

    print("wikidata.org labels were updated.")

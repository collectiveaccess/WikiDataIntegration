import sys
from pathlib import Path
from datetime import date
from os.path import exists
import json
import os
import fire

import utils.wiki_queries as wq

project_path = Path(__file__).resolve().parent.parent
sys.path.append(str(project_path))


constants_path = project_path / "scripts" / "constants"
today = date.today()


def download_all_properties():
    filepath = constants_path / f"wikdata_properties_{today}.json"

    # if file exists, do nothing
    if exists(filepath):
        print("wikidata.org labels were not updated.")
    # if file does not exist, delete old files, get properties, create new file
    else:
        for path in Path(constants_path).glob("wikdata_properties*.json"):
            os.remove(path)

        properties = wq.fetch_all_properties()
        with open(filepath, "w") as outfile:
            json_object = json.dumps(properties, indent=2)
            outfile.write(json_object)

        print("wikidata.org properties were updated.")


def download_all_external_id_properties():
    filepath = constants_path / f"wikdata_external_id_properties_{today}.json"

    # if file exists, do nothing
    if exists(filepath):
        print("wikidata.org labels were not updated.")
    # if file does not exist, delete old files, get properties, create new file
    else:
        for path in Path(constants_path).glob("wikdata_external_id_properties*.json"):
            os.remove(path)

        properties = wq.fetch_all_external_id_properties()
        with open(filepath, "w") as outfile:
            json_object = json.dumps(properties, indent=2)
            outfile.write(json_object)

        print("wikidata.org properties were updated.")


if __name__ == "__main__":
    fire.Fire()

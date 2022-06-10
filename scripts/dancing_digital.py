import sys
from pathlib import Path
import csv

import pywikibot
import utils.wikidata_utils as wd

data_path = Path(__file__).resolve().parent.parent / "data"
sys.path.append(str(data_path))

site = pywikibot.Site("wikidata", "wikidata")


with open(data_path / "venues.csv", mode="r") as file:
    csvFile = csv.DictReader(file)
    for line in csvFile:
        label = line["name"]
        res = wd.item_exists(site, label)

        print("----")
        print(line)
        if len(res) == 0:
            print("zero items found")
        else:
            print(f"{len(res)} items found")
            for r in res:
                print(r)

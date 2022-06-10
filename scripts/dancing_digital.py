import sys
from pathlib import Path
import pandas as pd
import pywikibot
import fire

import utils.wikidata_utils as wd

data_path = Path(__file__).resolve().parent.parent / "data"
sys.path.append(str(data_path))

files = ['people.csv', 'venues.csv', 'works.csv']


def preview_wikidata_records(filename):
    site = pywikibot.Site("wikidata", "wikidata")
    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        label = row["name"]
        res = wd.item_exists(site, label)

        print("----")
        print(row)
        if len(res) == 0:
            print("zero items found")
        else:
            print(f"{len(res)} items found")
            for r in res:
                print(r)


def save_wikidata_records(filename):
    """
    Read csv of people, venue, works. Connect to wikidata.org to find records
    that have same names. Create csv with found records.
    """
    site = pywikibot.Site("wikidata", "wikidata")
    rows = []
    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        label = row["name"]
        res = wd.item_exists(site, label)

        if len(res) > 0:
            for r in res:
                rows.append({"wikidata.org id": r['id'], "label": r['label'], "description": r['description']})

    new_df = pd.DataFrame(rows)
    new_df.to_csv(data_path / 'wikidata_org' / filename, index=False)


def preview_wikidata_all():
    for file in files:
        preview_wikidata_records(file)


def save_wikidata_all():
    for file in files:
        save_wikidata_records(file)


if __name__ == '__main__':
    fire.Fire({
        "preview_wikidata_all": preview_wikidata_all,
        'save_wikidata_all': save_wikidata_all,
    })

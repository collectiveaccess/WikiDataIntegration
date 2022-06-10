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


def create_local_records(filename, import_sitelinks):
    local_site = pywikibot.Site('en', 'cawikidev')
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    df = pd.read_csv(data_path / 'wikidata_org' / filename)
    for index, row in df.iterrows():
        results = wd.item_exists(local_site, row['label'])
        existing = False
        for result in results:
            if result['description'] == row['description'] and result['label'] == row['label']:
                existing = True
        if existing:
            continue

        item = pywikibot.ItemPage(repo, row['wikidata.org id'])
        item_dict = item.get()
        new_item = wd.import_item(local_site, item_dict, import_sitelinks)

        print('create_record:', row['label'])
        df.at[index, 'id'] = new_item.getID()
    df.to_csv(data_path / 'wikidata_org' / filename, index=False)



        new_item = wd.create_item(local_site, data)
        df.at[index, 'id'] = new_item.getID()

    df.to_csv(data_path / 'wikidata_org' / filename, index=False)


def preview_wikidata_all():
    for file in files:
        preview_wikidata_records(file)


def save_wikidata_all():
    for file in files:
        save_wikidata_records(file)


def create_local_all(import_sitelinks=True):
    for file in files:
        create_local_records(file, import_sitelinks)


if __name__ == '__main__':
    fire.Fire({
        "preview_wikidata_all": preview_wikidata_all,
        'save_wikidata_all': save_wikidata_all,
        'create_local_all': create_local_all,
    })

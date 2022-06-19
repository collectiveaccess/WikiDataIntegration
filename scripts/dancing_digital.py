import sys
from pathlib import Path
import pandas as pd
import pywikibot
import fire

import utils.wikidata_utils as wd

data_path = Path(__file__).resolve().parent.parent / "data"
sys.path.append(str(data_path))

files = ["people.csv", "venues.csv", "works.csv"]


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


def save_wikidata_to_csv(filename):
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
                rows.append(
                    {
                        "wikidata.org id": r["id"],
                        "label": r["label"],
                        "description": r["description"],
                    }
                )

    new_df = pd.DataFrame(rows)
    new_df.to_csv(data_path / "wikidata_org" / filename, index=False)


def create_existing_records(filename, import_sitelinks):
    local_site = pywikibot.Site("en", "cawikidev")
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    df = pd.read_csv(data_path / "wikidata_org" / filename)
    for index, row in df.iterrows():
        results = wd.item_exists(local_site, row["label"])
        existing = False
        for result in results:
            if (
                result["description"] == row["description"]
                and result["label"] == row["label"]
            ):
                existing = True
        if existing:
            continue

        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        new_item = wd.import_item(local_site, item_dict, import_sitelinks)

        print("create_record:", row["label"])
        df.at[index, "id"] = new_item.getID()
    df.to_csv(data_path / "wikidata_org" / filename, index=False)


def add_existing_claims(filename, import_sitelinks):
    local_site = pywikibot.Site("en", "cawikidev")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    df = pd.read_csv(data_path / "wikidata_org" / filename)
    for index, row in df.iterrows():
        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        local_item = pywikibot.ItemPage(local_repo, row["id"])
        print(index, row["label"])

        # iterate over all the wikidata.org claims
        for property, values in item_dict["claims"].items():
            for claim in values:
                new_claim_value = wd.convert_to_local_claim_value(
                    local_site, local_repo, claim, import_sitelinks
                )
                if new_claim_value:
                    try:
                        wd.add_claim(repo, local_item, property, new_claim_value)
                    except pywikibot.exceptions.OtherPageSaveError:
                        print(f"error add_claim: {row['label']}, {new_claim_value}")
                    except pywikibot.exceptions.APIMWError:
                        print(f"error add_claim: {row['label']}, {new_claim_value}")
                    except:
                        print(f"error add_claim: {row['label']}, {new_claim_value}")


def add_existing_sources_qualifiers(filename, import_sitelinks):
    local_site = pywikibot.Site("en", "cawikidev")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    df = pd.read_csv(data_path / "wikidata_org" / filename)
    for index, row in df.iterrows():
        print(index, row['label'])
        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        local_item = pywikibot.ItemPage(local_repo, row["id"])

        # iterate over all the wikidata.org claims
        for property, values in item_dict["claims"].items():
            # if property != "P2031":
            #     continue

            # print('--------------')
            # print('wikidata property', property )
            for claim in values:
                local_claim = None

                # print("claim", claim.id, wd.get_claim_value(claim))
                if claim.id in local_item.claims:
                    for l_claim in local_item.claims[claim.id]:
                        if wd.get_claim_value(l_claim, False) == wd.get_claim_value(
                            claim, False
                        ):
                            local_claim = l_claim
                            # print('local_claim', wd.get_claim_value(l_claim))

                if not local_claim:
                    continue

                for claim_source in claim.sources:
                    new_sources = []
                    # print("  claim_source", len(claim_source))
                    for source_property, source_values in claim_source.items():
                        # print('    property & values', source_property)

                        for source_claim in source_values:
                            source_value = wd.convert_to_local_claim_value(
                                local_site,
                                local_repo,
                                source_claim,
                                import_sitelinks,
                            )
                            # print('      source_value: ', source_value, wd.get_claim_value(source_claim))
                            exists = False
                            for l_source in local_claim.sources:
                                if source_property in l_source.keys():
                                    for lll_source in l_source[source_property]:
                                        if lll_source.getTarget() == source_value:
                                            exists = True
                            # print("exists", exists)

                            if not exists:
                                new_source = pywikibot.Claim(repo, source_property)
                                new_source.setTarget(source_value)
                                new_sources.append(new_source)

                    if len(new_sources) > 0:
                        # print('--add sources to claim', len(new_sources))
                        try:
                            local_claim.addSources(new_sources, summary="Adding sources.")
                        except pywikibot.exceptions.APIError as err:
                            print('sources not saved', property)


def preview_wikidata_all():
    for file in files:
        preview_wikidata_records(file)


def save_wikidata_to_csv_all():
    for file in files:
        save_wikidata_to_csv(file)


def create_existing_records_all(import_sitelinks=False):
    for file in files:
        create_existing_records(file, import_sitelinks)


def add_existing_claims_all(import_sitelinks=False):
    for file in files:
        add_existing_claims(file, import_sitelinks)


def add_existing_sources_qualifiers_all(import_sitelinks=False):
    for file in files:
        add_existing_sources_qualifiers(file, import_sitelinks)


if __name__ == "__main__":
    fire.Fire(
        {
            "preview_wikidata_all": preview_wikidata_all,
            "save_wikidata_to_csv_all": save_wikidata_to_csv_all,
            "create_existing_records_all": create_existing_records_all,
            "add_existing_claims_all": add_existing_claims_all,
            "add_existing_sources_qualifiers_all": add_existing_sources_qualifiers_all,
        }
    )
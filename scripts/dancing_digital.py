import sys
from pathlib import Path
import pandas as pd
import pywikibot
import fire

import utils.wikidata_utils as wd
from constants.languages import allowed_languages
from constants.wd_properties import properties

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
    Read csv of names. Connect to wikidata.org to find records
    that have same names. Create csv with all the found records.
    """
    site = pywikibot.Site("wikidata", "wikidata")
    rows = []
    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        # if row["name"] != "Pina Bausch":
        #     continue

        label = row["name"]
        results = wd.item_exists(site, label)

        if len(results) > 0:
            for result in results:
                rows.append(
                    {
                        "wikidata.org id": result["id"],
                        "label": result["label"],
                        "description": result["description"],
                        "language": result["language"],
                    }
                )

    new_df = pd.DataFrame(rows)
    new_df.to_csv(data_path / "wikidata_org" / filename, index=False)


def create_wikidata_records(filename, import_sitelinks):
    """Read csv of records from wikidata.org. Create item records in local
    wikibase instance."""
    local_site = pywikibot.Site("en", "cawiki")
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()


    df = pd.read_csv(data_path / "wikidata_org" / filename)
    for index, row in df.iterrows():
        # check if item exists in local site
        results = wd.item_exists(local_site, row["label"], row['language'])
        existing = False

        for result in results:
            # if no description, check if any of the existing records have same
            # label as the current row
            if pd.isna(row["description"]):
                if result["label"] == row["label"]:
                    existing = True
            # check if any of the existing records have same description and
            # label as current row
            elif 'label' in result and result['label']:
                if (
                    result["description"] == row["description"]
                    and result["label"] == row["label"]
                ):
                    existing = True
            elif 'aliases' in result:
                for alias in result['aliases']:
                    if (
                        result["description"] == row["description"]
                        and alias == row["label"]
                    ):
                        existing = True
        if existing:
            continue

        print(index, row['label'], existing)

        # add item from wikidata.org to local site
        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        new_item = wd.import_item(local_site, item_dict, import_sitelinks)

        if new_item:
            df.at[index, "id"] = new_item.getID()
            df.to_csv(data_path / "wikidata_org" / filename, index=False)


def add_wikidata_claims(filename, import_sitelinks):
    """Add claims to wikidata items."""
    local_site = pywikibot.Site("en", "cawiki")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    df = pd.read_csv(data_path / "wikidata_org" / filename)
    for index, row in df.iterrows():
        print(index, row["label"])

        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        local_item = pywikibot.ItemPage(local_repo, row["id"])

        # iterate over all the wikidata.org claims
        for property, values in item_dict["claims"].items():
            for claim in values:
                try:
                    new_claim_value = wd.convert_to_local_claim_value(
                        local_site, local_repo, claim, import_sitelinks
                    )
                except:
                    print(f"error new_claim_value: {row['label']}, {property}")

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


def create_dd_new_items(filename):
    """create records for dancing digital names that are not in wikidata.org"""
    site = pywikibot.Site("en", "cawiki")

    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        if pd.isna(row["id"]):
            data = {
                "descriptions": {"en": row["description"]},
                "labels": {"en": row["name"]},
            }
            new_item = wd.create_item(site, data)
            if new_item:
                df.at[index, "id"] = new_item.getID()

                df.to_csv(data_path / filename, index=False)


def add_dd_claims(filename):
    """add dancing digital claims to item records"""
    local_site = pywikibot.Site("en", "cawiki")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    res = wd.item_exists(local_site, "Dancing Digital")
    if len(res) == 1:
        dd_item = pywikibot.ItemPage(local_repo, res[0]["id"])
    else:
        raise ValueError("Dancing Digital record not found.")

    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        print(row["id"], row["name"])
        item = pywikibot.ItemPage(local_repo, row["id"])
        wd.add_claim(repo, item, properties["part of"], dd_item)


def add_dd_sources(filename):
    """add dancing digital claims to item records"""
    local_site = pywikibot.Site("en", "cawiki")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    res = wd.item_exists(local_site, "Dancing Digital")
    if len(res) == 1:
        dd_item = pywikibot.ItemPage(local_repo, res[0]["id"])
    else:
        raise ValueError("Dancing Digital record not found.")

    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        print(row["id"], row["name"])
        item = pywikibot.ItemPage(local_repo, row["id"])

        for claim in item.claims[properties["part of"]]:
            if claim.getTarget() == dd_item:
                wd.add_reference_date(repo, claim, properties["retrieved"])
                wd.add_reference(repo, claim, properties["stated in"], dd_item)



def preview_wikidata_all():
    for file in files:
        preview_wikidata_records(file)


def save_wikidata_to_csv_all():
    for file in files:
        save_wikidata_to_csv(file)


def create_wikidata_records_all(import_sitelinks=False):
    for file in files:
        create_wikidata_records(file, import_sitelinks)


def add_wikidata_claims_all(import_sitelinks=False):
    for file in files:
        add_wikidata_claims(file, import_sitelinks)


def create_dd_new_items_all():
    for file in files:
        create_dd_new_items(file)


def add_dd_claims_all():
    for file in files:
        add_dd_claims(file)


def add_dd_sources_all():
    for file in files:
        add_dd_sources(file)


def test_invalid_lanuages():
    local_site = pywikibot.Site("en", "cawiki")
    repo = local_site.data_repository()
    item = pywikibot.ItemPage(repo, "Q592")

    for lan in allowed_languages:
        try:
            item.editEntity({"labels": {lan: f"foo {lan}"}})
        except:
            print(lan, "invalid")


if __name__ == "__main__":
    fire.Fire(
        {
            "preview_wikidata_all": preview_wikidata_all,
            "save_wikidata_to_csv_all": save_wikidata_to_csv_all,
            "create_wikidata_records_all": create_wikidata_records_all,
            "add_wikidata_claims_all": add_wikidata_claims_all,
            "create_dd_new_items_all": create_dd_new_items_all,
            "add_dd_claims_all": add_dd_claims_all,
            "add_dd_sources_all": add_dd_sources_all,
            "test_invalid_lanuages": test_invalid_lanuages
        }
    )

import sys
from pathlib import Path
import pandas as pd
import pywikibot
import fire

import utils.wikidata_utils as wd
import utils.wiki_queries as wq
from constants.wd_properties import properties
from utils.logger import logger

data_path = Path(__file__).resolve().parent.parent / "data"
sys.path.append(str(data_path))

files = ["people.csv", "venues.csv", "works.csv"]


def preview_wikidata_records(filename):
    site = pywikibot.Site("wikidata", "wikidata")
    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        label = row["name"]
        res = wq.search_keyword(site, label)

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
        results = wq.search_keyword(site, label)

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
        # if row['label'] != 'Pina Bausch and the Tanztheater':
        #     continue

        # check if item exists in local site
        results = wq.search_keyword(local_site, row["label"], row["language"])
        existing = False

        for result in results:
            # if no description, check if any of the existing records have same
            # label as the current row
            if pd.isna(row["description"]):
                if result["label"] == row["label"]:
                    existing = True
            # check if any of the existing records have same description and
            # label as current row
            elif "label" in result and result["label"]:
                if (
                    result["description"] == row["description"]
                    and result["label"] == row["label"]
                ):
                    existing = True

        if existing:
            continue

        print(index, row["label"], existing)

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
        # if index != 28:
        #     continue

        print(index, row["label"], row["id"])

        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        local_item = pywikibot.ItemPage(local_repo, row["id"])

        # iterate over all the wikidata.org claims
        for property, values in item_dict["claims"].items():
            for claim in values:
                # if claim.id != 'P2048':
                #     continue

                new_claim_value = wd.convert_to_local_claim_value(
                    local_site, local_repo, claim, import_sitelinks
                )
                if new_claim_value:
                    wd.add_claim(repo, local_item, property, new_claim_value)


def console(*args):
    # print(args)
    pass


def update_wikidata_claims(filename, import_sitelinks):
    """add sources to wikidata claims."""
    local_site = pywikibot.Site("en", "cawiki")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    df = pd.read_csv(data_path / "wikidata_org" / filename)
    for index, row in df.iterrows():
        # if index < 16:
        #     continue
        # if row['id'] != 'Q567':
        #     continue

        print(index, row["label"], row["id"])

        item = pywikibot.ItemPage(repo, row["wikidata.org id"])
        item_dict = item.get()
        local_item = pywikibot.ItemPage(local_repo, row["id"])

        # iterate over all the wikidata.org claims
        for property, claims in item_dict["claims"].items():
            # if property != "P54":
            #     continue

            console("--------------")
            console("wikidata property", property)

            for claim in claims:
                # skip commonsMedia claims since we don't import them
                if claim.type == "commonsMedia":
                    continue

                console("claim", claim.id, wd.get_claim_value(claim))

                # get the corresponding local claim
                if claim.id in local_item.claims:
                    for l_claim in local_item.claims[claim.id]:

                        if wd.get_claim_value(l_claim, False) == wd.get_claim_value(
                            claim, False
                        ):
                            local_claim = l_claim
                            console(
                                "local_claim", l_claim.id, wd.get_claim_value(l_claim)
                            )

                add_source_to_wikidata_claim(row, claim, local_claim, import_sitelinks)
                add_qualifier_to_wikidata_claim(
                    row, claim, local_claim, import_sitelinks
                )


def add_qualifier_to_wikidata_claim(row, claim, local_claim, import_sitelinks):
    local_site = pywikibot.Site("en", "cawiki")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    # claim.qualifiers returns an ordered dictionary
    for qualifier_property, qualifier_claims in claim.qualifiers.items():
        console("    property & values", qualifier_property)

        for qualifier_claim in qualifier_claims:
            qualifier_value = wd.convert_to_local_claim_value(
                local_site,
                local_repo,
                qualifier_claim,
                import_sitelinks,
            )
            console(
                "      qualifier_value: ",
                qualifier_value,
                wd.get_claim_value(qualifier_claim),
            )

            # check is source exists locally
            exists = False
            if qualifier_property in local_claim.qualifiers:
                for l_source in local_claim.qualifiers[qualifier_property]:
                    if l_source.getTarget() == qualifier_value:
                        exists = True
            console("exists", exists)

            # add new source claim
            if not exists:
                try:
                    new_claim = pywikibot.Claim(repo, qualifier_property)
                    new_claim.setTarget(qualifier_value)
                    local_claim.addQualifier(new_claim, summary="Add qualifier.")
                    logger.info(
                        f"Add qualifier: {claim.id} "
                        f"{qualifier_property} {qualifier_value}"
                    )
                except:
                    logger.error(
                        f"Qualifier not added: {claim.id} "
                        f"{qualifier_property} {qualifier_value}"
                    )


def add_source_to_wikidata_claim(row, claim, local_claim, import_sitelinks):
    local_site = pywikibot.Site("en", "cawiki")
    local_repo = local_site.data_repository()
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    # claim.sources returns a list or ordered dictionariers
    for claim_source in claim.sources:
        new_sources = []
        console("  claim_source", len(claim_source))
        for source_property, source_values in claim_source.items():
            console("    property & values", source_property)

            # NOTE:skip P4656 "Wikimedia import URL"
            # since we don't have wikipedia pages.
            # https://phabricator.wikimedia.org/T301243
            if source_property in ["P4656"]:
                continue
            # NOTE: skip reference url since there is a bug with saving URL
            if source_property in ["P854"]:
                continue

            for source_claim in source_values:
                source_value = wd.convert_to_local_claim_value(
                    local_site,
                    local_repo,
                    source_claim,
                    import_sitelinks,
                )
                console(
                    "      source_value: ",
                    source_value,
                    wd.get_claim_value(source_claim),
                )

                # check is source exists locally
                exists = False
                for l_source in local_claim.sources:
                    if source_property in l_source.keys():
                        for ll_source in l_source[source_property]:
                            if ll_source.getTarget() == source_value:
                                exists = True
                console("exists", exists)

                # add new source claim
                if not exists:
                    try:
                        new_source = pywikibot.Claim(repo, source_property)
                        new_source.setTarget(source_value)
                    except:
                        print("new_source target", source_property)
                    new_sources.append(new_source)

        if len(new_sources) > 0:
            console("--add sources to claim", len(new_sources))
            try:
                local_claim.addSources(new_sources, summary="Adding sources.")
                logger.info(f'Sources added: {row["id"]} {local_claim.id}')
            except:
                logger.error(f'Sources not saved: {row["id"]} {local_claim.id}')


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

    res = wq.search_keyword(local_site, "Dancing Digital")
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

    res = wq.search_keyword(local_site, "Dancing Digital")
    if len(res) == 1:
        dd_item = pywikibot.ItemPage(local_repo, res[0]["id"])
    else:
        raise ValueError("Dancing Digital record not found.")

    df = pd.read_csv(data_path / filename)
    for index, row in df.iterrows():
        print(row["id"], row["name"])
        item = pywikibot.ItemPage(local_repo, row["id"])

        for claim in item.claims[properties["part of"]]:
            if claim.target == dd_item:
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


def update_wikidata_claims_all(import_sitelinks=False):
    for file in files:
        update_wikidata_claims(file, import_sitelinks)


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


def create_basic_dd_records():
    site = pywikibot.Site("en", "cawiki")

    data = {
        "labels": {
            "en": "Dancing Digital",
        },
        "descriptions": {
            "en": "dance catalog project",
        },
    }
    wd.create_item(site, data)


def test_invalid_languages():
    """find which languages are not allowed in wikibase instance"""
    local_site = pywikibot.Site("en", "cawiki")
    repo = local_site.data_repository()
    item = pywikibot.ItemPage(repo, "Q592")

    tmp = ["pcm"]
    for lan in tmp:
        try:
            print(lan)
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
            "update_wikidata_claims_all": update_wikidata_claims_all,
            "create_basic_dd_records": create_basic_dd_records,
            "create_dd_new_items_all": create_dd_new_items_all,
            "add_dd_claims_all": add_dd_claims_all,
            "add_dd_sources_all": add_dd_sources_all,
            "test_invalid_languages": test_invalid_languages,
        }
    )

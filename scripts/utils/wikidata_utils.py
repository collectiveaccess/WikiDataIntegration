from datetime import date
import sys
from pathlib import Path
import pywikibot
import time
import re

from scripts.utils.logger import logger
from scripts.constants.languages import invalid_languages
import scripts.utils.wiki_queries as wq
import scripts.utils.wiki_serialization as ws

constants_path = Path(__file__).resolve().parent.parent / "constants"
sys.path.append(str(constants_path))


def validate_create_data(data, key):
    if key not in data:
        raise ValueError(f"create_item: {key} is required")

    if key not in ["labels", "descriptions", "sitelinks", "aliases"]:
        raise ValueError(f"create_item: {key} is not a valid key")

    if key in data:
        if not isinstance(data[key], dict):
            raise ValueError(f"create_item: {key} must be a dictionary")

        if len(data[key].keys()) == 0:
            raise ValueError(f"create_item: {key} must be a dictionary")


def create_item(site, data, validation=True):
    """create wikidata item (Q id record)."""
    if validation:
        validate_create_data(data, "labels")
        validate_create_data(data, "descriptions")

    repo = site.data_repository()
    new_item = pywikibot.ItemPage(repo)
    results = edit_entity(new_item, data)

    # return new item if new item was created
    # id -1 means that item record was not created
    if new_item.id != "-1":
        logger.info(f"Item created: {new_item.id}")
        return new_item
    # return results if it is is pywikibot ItemPage
    elif hasattr(results, "data_item"):
        return results


def edit_labels(item, new_labels):
    """Edit labels for a given item"""
    for lang, value in new_labels.items():
        item.editLabels(labels={lang: value}, summary=f"Setting label: {value}")


def edit_descriptions(item, new_descriptions):
    """edit descriptions for a given item"""
    for lang, value in new_descriptions.items():
        item.editDescriptions({lang: value}, summary=f"Setting description: {value}")


def edit_entity(item, data):
    """edit label, description, alias and sitelinks for a given item"""
    try:
        item.editEntity(data, summary="Setting item data.")
        return item
    except pywikibot.exceptions.OtherPageSaveError as err:
        if hasattr(err.reason, "code") and err.reason.code == "not-recognized-language":
            langs = set()
            for key in data.keys():
                langs.update(data[key].keys())
        else:
            # return existing item if item with label and description exists
            text = "wikibase-validator-label-with-description-conflict"
            if text in err.args:
                matches = re.search(r"Item:(Q\d+)", err.args)

                if matches:
                    qid = matches.groups()[0]
                    repo = item.data_repository
                    return pywikibot.ItemPage(repo, qid)

            logger.error(f"Could not edit item *: {err}")
    except:
        if "en" in data["labels"]:
            lang = "en"
        else:
            for k, v in data["labels"].items():
                lang = k

        logger.error(f"Could not edit item: {data['labels'][lang]} {item.id}")


def edit_aliases(item, new_alias):
    """edit aliases for a given item"""
    for lang, value in new_alias.items():
        item.editAliases({lang: value}, summary=f"Set aliases: {value}")


def edit_sitelink(item, site, title):
    """edit sitelinks for a given tiem"""
    sitedict = {"site": site, "title": title}
    item.setSitelink(sitedict, summary=f"Set sitelink: {title}")


def remove_sitelink(item, site):
    """remove sitelinks from a given item"""
    item.removeSitelink(site)


def add_claim(repo, item, property, value):
    """add claim to an item"""
    # return claim if it exists
    if property in item.claims:
        for claim in item.claims[property]:
            if claim.target == value:
                return claim

    # create new claim
    new_claim = pywikibot.Claim(repo, property)
    try:
        new_claim.setTarget(value)
        item.addClaim(new_claim, summary="Add claim.")
        logger.info(f"Add claim: {item.id} {property} {value}")
        return new_claim
    except:
        logger.error(f"Could not add claim: {item.id} {property} {value}")


def remove_claim(item, property):
    """remove claim from an item"""
    if property not in item.claims:
        return

    for claim in item.claims[property]:
        item.removeClaims(claim, summary="Remove claim.")
        logger.info(f"Remove claim: {item.id} {property}")


def add_qualifier(repo, claim, property, value):
    """add qualifier to a claim"""
    # return qualifier if it exists
    if property in claim.qualifiers:
        for qualifier in claim.qualifiers[property]:
            if qualifier.getTarget() == value:
                return qualifier

    # create new qualifier
    new_qualifier = pywikibot.Claim(repo, property)
    new_qualifier.setTarget(value)
    claim.addQualifier(new_qualifier, summary="Add qualifier.")
    logger.info(f"Add qualifier: {claim.id} {property} {value}")
    return new_qualifier


def remove_qualifier(item, statement_property, qualifier_property):
    """remove qualifier from a claim"""
    if statement_property not in item.claims:
        return

    for claim in item.claims[statement_property]:
        if qualifier_property not in claim.qualifiers:
            continue

        for qualifier in claim.qualifiers[qualifier_property]:
            try:
                claim.removeQualifier(qualifier, summary="Remove qualifier.")
                logger.info(f"Remove qualifier: {item.id} {qualifier_property}")
            except:
                logger.error(
                    f"Could not delete qualifier {item.id} {qualifier_property}"
                )


def add_reference(repo, claim, property, value):
    """add reference to a claim"""
    for source in claim.getSources():
        if property in source:
            for old_claim in source[property]:
                if old_claim.target == value:
                    return old_claim

    new_source = pywikibot.Claim(repo, property)
    new_source.setTarget(value)
    try:
        claim.addSources([new_source], summary="Adding sources.")
        logger.info(f"Add source: {claim.id} {property} {value}")
    except:
        logger.error(f"add_reference error: {claim.id} {property} {value}")


def add_reference_date(repo, claim, property, source_date=date.today()):
    """add date as reference for a claim"""
    value = pywikibot.WbTime(
        site=repo,
        year=int(source_date.strftime("%Y")),
        month=int(source_date.strftime("%m")),
        day=int(source_date.strftime("%d")),
    )
    add_reference(repo, claim, property, value)


def remove_reference(item, statement_property, reference_property):
    """add remove reference from claims"""

    if statement_property not in item.claims:
        return

    sources = []
    for claim in item.claims[statement_property]:
        for old_source in claim.getSources():
            for old_claims in old_source.values():
                for old_claim in old_claims:
                    if old_claim.getID() == reference_property:
                        sources.append(old_claim)

        if len(sources) > 0:
            claim.removeSources(sources, summary="Removed sources.")
            logger.info(f"Remove sources: {claim.id} {reference_property}")


def import_item(site, item_dict, import_sitelinks=True):
    """import an item record from wikidata."""
    ws.remove_identical_label_description(item_dict)
    data = {}
    for key, values in item_dict.items():
        if key in ["labels", "descriptions", "aliases"]:
            if len(values) > 0:
                data[key] = {
                    k: v for k, v in values.items() if k not in invalid_languages
                }
        elif key == "sitelinks":
            if import_sitelinks and len(item_dict[key]) > 0:
                data[key] = [{k: v.title} for k, v in item_dict[key].items()]
        elif key == "claims":
            continue
        else:
            print(f"{key} not imported")

    return create_item(site, data, validation=False)


def get_claim_language(claim_dict):
    if "en" in claim_dict["labels"]:
        lang = "en"
    else:
        lang = [k for k, v in claim_dict["labels"].items()][0]

    return lang


def convert_to_local_claim_value(site, repo, claim, import_sitelinks):
    """When importing claims from wikidata.org, they often refer to items records
    (Q id) that exists in wikidata.org. This method searches if the item record
    exists in the local wikidata. If record exists, return the record
    from local wikidata. If record does not exists, create record in local
    wikidata, and return new record."""

    claim_value = claim.target
    if not claim_value:
        return

    if claim.type == "globe-coordinate":
        return pywikibot.Coordinate(
            site=repo, lat=claim_value.lat, lon=claim_value.lon, precision=0.0001
        )

    elif claim.type == "quantity":
        if not claim_value.get_unit_item():
            return claim_value

        unit_dict = claim_value.get_unit_item().get()
        lang = get_claim_language(unit_dict)

        # check if unit exists locally
        results = wq.search_keyword(site, unit_dict["labels"][lang])
        existing = False
        for result in results:
            if (
                result["description"] == unit_dict["descriptions"][lang]
                and result["label"] == unit_dict["labels"][lang]
            ):
                existing = True
                new_unit_value = pywikibot.ItemPage(repo, result["id"])
        # if unit doesn't exists locally, import it
        if not existing:
            new_unit_value = import_item(site, unit_dict, import_sitelinks)
        unit = new_unit_value.full_url().replace("wiki/Item%3A", "entity/")
        return pywikibot.WbQuantity(amount=claim_value.amount, unit=unit, site=site)

    elif claim.type == "wikibase-item":
        claim_item_dict = claim_value.get()
        lang = get_claim_language(claim_item_dict)

        # check if claim item exists locally
        results = wq.search_keyword(site, claim_item_dict["labels"][lang], lang)
        existing = False

        for result in results:
            if result["description"]:
                if (
                    result["description"] == claim_item_dict["descriptions"][lang]
                    and result["label"] == claim_item_dict["labels"][lang]
                ):
                    existing = True
                    new_claim_value = pywikibot.ItemPage(repo, result["id"])
            elif result["label"] == claim_item_dict["labels"][lang]:
                existing = True
                new_claim_value = pywikibot.ItemPage(repo, result["id"])

        # if claim item doesn't exists locally, import it
        if not existing:
            new_claim_value = import_item(site, claim_item_dict, import_sitelinks)
        return new_claim_value

    elif claim.type == "commonsMedia":
        return
    else:
        return claim_value


def add_nested_ids(claim_type, claim_ids):
    """get q ids for certain claim types"""
    if claim_type.type == "wikibase-item" and claim_type.target:
        claim_ids.add(claim_type.target.id)

    if claim_type.type == "quantity" and claim_type.target:
        if claim_type.target.unit != "1":
            # target.unit is the url for wikidata item record
            unit_url = claim_type.target.unit
            id = unit_url.split("/")[-1]
            claim_ids.add(id)


def get_ids_for_item(item, item_json, include_pids=True, include_qids=True):
    """iterate through an item to get all item Q ids and property P ids"""
    claim_ids = set()

    if include_pids and "claims" in item_json:
        claim_ids.update([prop for prop in item_json["claims"]])

    for prop, claims in item.claims.items():
        if include_pids:
            claim_ids.add(prop)

        for claim in claims:
            if include_qids:
                add_nested_ids(claim, claim_ids)

            if include_pids:
                if claim.type == "wikibase-property" and claim.target:
                    claim_ids.add(claim.target.getID())

            for source_dict in claim.sources:
                for prop, sources in source_dict.items():
                    if include_pids:
                        claim_ids.add(prop)
                    if include_qids:
                        for source in sources:
                            add_nested_ids(source, claim_ids)

            for prop, qualifiers in claim.qualifiers.items():
                if include_pids:
                    claim_ids.add(prop)
                if include_qids:
                    for qualifier in qualifiers:
                        add_nested_ids(qualifier, claim_ids)

    if len(claim_ids) > 0:
        return list(claim_ids)
    else:
        return []


def get_commons_media_for_item(item):
    """iterate through an item to get all commons media"""
    media = set()

    for prop, claims in item.claims.items():
        for claim in claims:
            if claim.type == "commonsMedia" and claim.target:
                media.add(claim.target.title())

            for source_dict in claim.sources:
                for prop, sources in source_dict.items():
                    for source in sources:
                        if source.type == "commonsMedia" and claim.target:
                            media.add(source.target.title())

            for prop, qualifiers in claim.qualifiers.items():
                for qualifier in qualifiers:
                    if qualifier.type == "commonsMedia" and claim.target:
                        media.add(qualifier.target.title())
    return list(media)


def create_id_label_dictionary(item, item_json):
    """create dictionary with ids (item Q id and property P id) and their labels"""
    ids = get_ids_for_item(item, item_json, include_pids=True, include_qids=True)

    # connect to wikidata.org API to get labels for a list of ids
    if len(ids) > 0:
        return wq.fetch_and_format_labels_for_ids_sqarql(ids)
    else:
        return {}


def get_all_language_codes_for_item(item):
    """get all the language codes in an item"""
    item_lang_codes = set()

    for lang, value in item.labels.items():
        item_lang_codes.add(lang)
    for lang, value in item.descriptions.items():
        item_lang_codes.add(lang)
    for lang, value in item.aliases.items():
        item_lang_codes.add(lang)

    return item_lang_codes


def format_display_item(item, site):
    """takes the json from a item and reshapes it to fit the needs of the
    of our /items/{id} API endpoint
    """
    data = {}
    item_json = item.toJSON()

    s1 = time.time()
    # reshape json to create {language: value} dictionary
    for field in ["labels", "descriptions", "aliases"]:
        if field in item_json:
            if field == "aliases":
                data[field] = ws.format_item_aliases(item_json)
            else:
                data[field] = ws.format_item_field(item_json, field)

    s2 = time.time()
    print("basic", s2 - s1)

    # create {item_id: label, property_id: label} dictionary so we can
    # include labels in api response
    id_label_dict = create_id_label_dictionary(item, item_json)

    s3 = time.time()
    print("create_id_label_dictionary", s3 - s2)

    # get metadata for every commons media that is associated with this item
    # so we can add media metadata to api response
    media_files = get_commons_media_for_item(item)
    media_metadata = wq.fetch_and_format_commons_media_metadata_results(
        site, media_files
    )

    s4 = time.time()
    print("media_files", s4 - s3)

    # get links for external ids in this item so we can add links for
    # external id to api response
    external_id_links = wq.fetch_and_format_external_id_links(item.id)

    s5 = time.time()
    print("external_id_links", s5 - s4)

    tmp = ws.format_item_claims(item, id_label_dict, media_metadata, external_id_links)
    data["statements"] = tmp["statements"]
    data["identifiers"] = tmp["identifiers"]

    s6 = time.time()
    print("claims", s6 - s5)

    # get all the language names for the all the language codes in an item
    item_lang_codes = get_all_language_codes_for_item(item)
    langs_dict = wq.fetch_and_format_item_languages(site, item_lang_codes)
    data["languages"] = langs_dict
    data["id"] = item.id

    s7 = time.time()
    print("end", s7 - s6)

    return data


def login(my_site):
    # use userinfo to read cookie. must run userinfo before logged_in.
    my_site.userinfo.get("id")

    # if valid cookie, return
    if my_site.logged_in():
        return

    # get password from password file
    pywikibot.login.LoginManager(site=my_site).readPassword()

    # login to site
    pywikibot.data.api.LoginManager(site=my_site).login()
    my_site.login()

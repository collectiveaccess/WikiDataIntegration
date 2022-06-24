from datetime import date
import re
import sys
from pathlib import Path
import json
import requests
import pywikibot
from pywikibot.data import api

from utils.logger import logger
from constants.languages import invalid_languages, allowed_languages

data_path = Path(__file__).resolve().parent.parent.parent / "data"
sys.path.append(str(data_path))


WIKI_BASE_URL = "https://www.wikidata.org"
WIKI_QUERY_URL = "https://query.wikidata.org"


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
    edit_entity(new_item, data)

    # id -1 means that item record was not created
    if new_item.id != "-1":
        logger.info(f"Item created: {new_item.id}")
        return new_item


def item_exists(site, keyword, language="en"):
    """search wikidata for a given keyword"""
    # https://stackoverflow.com/a/45050455
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": language,
        "type": "item",
        "search": keyword,
    }
    api_request = api.Request(site=site, parameters=params)
    result = api_request.submit()

    return process_item_exists_results(result["search"], language)


def process_item_exists_results(results, language):
    """format search results from wikidata"""
    count = len(results)
    if count == 0:
        return []
    else:
        tmp = []
        for result in results:
            description = result["description"] if "description" in result else None
            if "label" in result:
                label = result["label"]
            elif "aliases" in result:
                label = result["aliases"][0]
            else:
                label = None

            tmp.append(
                {
                    "id": result["id"],
                    "label": label,
                    "description": description,
                    "url": result["url"],
                    "language": language,
                }
            )
        return tmp


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
        if err.reason.code == "not-recognized-language":
            langs = set()
            for key in data.keys():
                langs.update(data[key].keys())

            print(langs - set(allowed_languages))
        else:
            logger.error(f"Could not edit item: {err}")
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
    remove_identical_label_description(item_dict)
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
        results = item_exists(site, unit_dict["labels"][lang])
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
        results = item_exists(site, claim_item_dict["labels"][lang], lang)
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


def remove_identical_label_description(claim_item_dict):
    """remove description if it has same value as label"""
    if "labels" not in claim_item_dict:
        return
    if "descriptions" not in claim_item_dict:
        return

    new_descriptions = {}
    for lang, v in claim_item_dict["labels"].items():
        if lang not in claim_item_dict["descriptions"]:
            continue

        if claim_item_dict["labels"][lang] != claim_item_dict["descriptions"][lang]:
            new_descriptions[lang] = claim_item_dict["descriptions"][lang]
        else:
            logger.warning(
                f"'{claim_item_dict['descriptions'][lang]}': "
                f"{lang} description removed because it is the same as label"
            )

    claim_item_dict["descriptions"] = new_descriptions


def extract_description_from_image_data(claim, text):
    match = re.search("\|[dD]escription={{(.*?)}}\s+\|", text)
    if match:
        description = match.groups()[0]
        match = re.search("([a-z]+)\|[0-9]+=(.*?)$", description)
        if match:
            value = {"url": claim.target.full_url(), "lang": match[1], "text": match[2]}
        else:
            value = {"url": claim.target.full_url(), "text": description}
    else:
        match = re.search("\|[dD]escription=(.*?)\s+\|", text)
        if match:
            value = {"url": claim.target.full_url(), "text": match[1]}
        else:

            value = {"url": claim.target.full_url(), "text": claim.target.title()}

    return value


def get_claim_value(claim, include_qid=False):
    """get the text value of a claim"""
    if claim.type == "wikibase-item":
        if not claim.getTarget():
            return

        claim_dict = claim.get()
        lang = get_claim_language(claim_dict)
        label = claim_dict["labels"][lang]

        if include_qid:
            value = claim.target.title() + " " + label
        else:
            value = label
    elif claim.type == "time":
        value = claim.target.toTimestr()
    elif claim.type == "globe-coordinate":
        value = {"latitude": claim.getTarget().lat, "longitude": claim.getTarget().lon}
    elif claim.type == "quantity":
        if claim.target.unit == "1":
            value = claim.target.amount.to_eng_string()
        else:
            unit_dict = claim.target.get_unit_item().get()
            lang = get_claim_language(unit_dict)
            value = (
                claim.target.amount.to_eng_string() + " " + unit_dict["labels"][lang]
            )
    elif claim.type == "commonsMedia":
        value = extract_description_from_image_data(claim, claim.target.text)
    elif claim.type == "monolingualtext":
        value = claim.target.text
    elif claim.type == "geo-shape":
        value = claim.target.toWikibase()
    else:
        value = claim.getTarget()

    return value


def fetch_all_wikidata_properties():
    """
    get all properties from wikidata

    https://stackoverflow.com/questions/25100224/how-to-get-a-list-of-all-wikidata-properties
    """

    link = f"{WIKI_QUERY_URL}/sparql?format=json&query=SELECT%20%3Fproperty%20%3FpropertyLabel%20WHERE%20%7B%0A%20%20%20%20%3Fproperty%20a%20wikibase%3AProperty%20.%0A%20%20%20%20SERVICE%20wikibase%3Alabel%20%7B%0A%20%20%20%20%20%20bd%3AserviceParam%20wikibase%3Alanguage%20%22en%22%20.%0A%20%20%20%7D%0A%20%7D%0A%0A"
    response = requests.get(link)
    results = response.json()["results"]["bindings"]

    data = {}
    for result in results:
        property = result["property"]["value"].split("/")[-1]
        value = result["propertyLabel"]["value"]
        data[property] = value

    return data


def fetch_labels_for_ids(ids, lang="en"):
    """
    get labels for a given list of Q ids and property ids from wikidata

    https://stackoverflow.com/questions/29179564/get-description-of-a-wikidata-property
    https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities
    """

    # split ids list into multiple lists because wikidata API has max limit of 50 ids
    chunk_size = 50
    chunked_list = [ids[i : i + chunk_size] for i in range(0, len(ids), chunk_size)]

    data = {}

    for chunk_ids in chunked_list:
        ids_str = "|".join(chunk_ids)
        link = f"{WIKI_BASE_URL}/w/api.php?action=wbgetentities&ids={ids_str}&props=labels&languages={lang}&format=json"
        response = requests.get(link)

        if response.status_code == 200:
            json = response.json()
            if "error" not in json:
                results = json["entities"]
                for prop, value in results.items():
                    if "labels" in value and lang in value["labels"]:
                        data[prop] = value["labels"][lang]["value"]
                    else:
                        data[prop] = ""
            else:
                raise ValueError(json["error"]["info"])
        else:
            raise ValueError("Could not get labels for ids from wikidata API.")

    return data


def get_ids_for_item(item, item_json, include_pids=True, include_qids=True):
    """get all Q ids and property ids for an item."""
    claim_ids = set()

    if include_pids:
        claim_ids.update([prop for prop in item_json["claims"]])

    for prop, claims in item.claims.items():
        if include_pids:
            claim_ids.add(prop)

        if include_qids:
            for claim in claims:
                if claim.type == "wikibase-item":
                    claim_ids.add(claim.target.title())

        for claim in claims:
            for source_dict in claim.sources:
                for prop, sources in source_dict.items():
                    if include_pids:
                        claim_ids.add(prop)
                    if include_qids:
                        for source in sources:
                            if source.type == "wikibase-item":
                                claim_ids.add(source.target.title())

            for prop, qualifiers in claim.qualifiers.items():
                if include_pids:
                    claim_ids.add(prop)
                if include_qids:
                    for qualifier in qualifiers:
                        if qualifier.type == "wikibase-item":
                            claim_ids.add(qualifier.target.title())

    return list(claim_ids)


def format_display_claim(claim, prop, ids_dict):
    """created a nested dictionary for an claims data"""

    data = {
        "property": prop,
        "property_value": ids_dict[prop],
        "data_type": claim.type,
        "data_value": {},
    }
    if claim.type == "wikibase-item":
        qid = claim.target.title()
        data["data_value"]["id"] = qid
        data["data_value"]["value"] = ids_dict[qid]
        data["data_value"]["url"] = claim.target.full_url()
    elif claim.type == "geo-shape":
        data["data_value"]["value"] = get_claim_value(claim)
        data["data_value"]["url"] = claim.target.page.full_url()
    else:
        data["data_value"]["value"] = get_claim_value(claim)

    return data


def format_ids_labels(item, item_json):
    """create dictionary with property ids / item ids and their labels"""
    qids = get_ids_for_item(item, item_json, include_pids=False, include_qids=True)
    pids = get_ids_for_item(item, item_json, include_pids=True, include_qids=False)

    # connect to wikidata.org API to get labels for qids
    ids_dict = fetch_labels_for_ids(qids, lang="en")

    # read file to get labels for pids
    for path in Path(data_path).glob("wikdata_labels*.json"):
        with open(str(path), "r") as file:
            properties = json.loads(file.read())
            for pid in pids:
                ids_dict[pid] = properties[pid]

    return ids_dict


def format_display_item_claims(item, item_json):
    """created a nested dictionary for an item claims, references, and qualifiers data"""
    ids_dict = format_ids_labels(item, item_json)

    data = {}
    for prop, claims in item.claims.items():
        data[prop] = []

        for claim in claims:
            claim_data = {
                **format_display_claim(claim, prop, ids_dict),
                "id": claim.snak,
            }

            if claim.qualifiers:
                claim_data["qualifiers"] = {}

            if claim.sources:
                claim_data["references"] = []

            for prop_q, qualifiers in claim.qualifiers.items():
                claim_data["qualifiers"][prop_q] = []
                for qualifier in qualifiers:
                    qualifier_data = format_display_claim(qualifier, prop_q, ids_dict)
                    claim_data["qualifiers"][prop_q].append(qualifier_data)

            for source_dict in claim.sources:
                source_dict_data = {}
                for prop_s, sources in source_dict.items():
                    source_dict_data[prop_s] = []
                    for source in sources:
                        source_data = format_display_claim(source, prop_s, ids_dict)
                        source_dict_data[prop_s].append(source_data)

                claim_data["references"].append(source_dict_data)

            data[prop].append(claim_data)

    return data


def format_item_field(item_json, type):
    return {lang: values["value"] for lang, values in item_json[type].items()}


def format_item_aliases(item_json):
    data = {}
    for lang, values in item_json["aliases"].items():
        data[lang] = []
        for value in values:

            data[lang].append(value["value"])

    return data


def format_display_item(item):
    """created a nested dictionary for an item data"""
    data = {}
    item_json = item.toJSON()

    for field in ["labels", "descriptions", "aliases"]:
        if field in item_json:
            if field == "aliases":
                data[field] = format_item_aliases(item_json)
            else:
                data[field] = format_item_field(item_json, field)

    data["claims"] = format_display_item_claims(item, item_json)

    return data

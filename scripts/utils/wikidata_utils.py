from datetime import date
import re
import sys
from pathlib import Path
import pywikibot

from utils.logger import logger
from constants.languages import invalid_languages, allowed_languages
import utils.wiki_queries as wq

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
    edit_entity(new_item, data)

    # id -1 means that item record was not created
    if new_item.id != "-1":
        logger.info(f"Item created: {new_item.id}")
        return new_item


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


def remove_identical_label_description(claim_item_dict):
    """remove description if it has same value as label. Wikibase does not allow
    a label and description to be equal"""
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


def add_nested_ids(claim_type, claim_ids):
    """get q ids for certain claim types"""
    if claim_type.type == "wikibase-item" and claim_type.target:
        claim_ids.add(claim_type.target.title())

    if claim_type.type == "quantity" and claim_type.target:
        if claim_type.target.unit != "1":
            # target.unit is the url for wikidata item record
            unit_url = claim_type.target.unit
            id = unit_url.split("/")[-1]
            claim_ids.add(id)


def get_ids_for_item(item, item_json, include_pids=True, include_qids=True):
    """iterate through an item to get all item Q ids and property P ids"""
    claim_ids = set()

    if include_pids:
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

    return list(claim_ids)


def get_commons_media_for_item(item):
    """iterate through an item to get all commons media"""
    media = set()

    for prop, claims in item.claims.items():
        for claim in claims:
            if claim.type == "commonsMedia":
                media.add(claim.target.title())

            for source_dict in claim.sources:
                for prop, sources in source_dict.items():
                    for source in sources:
                        if source.type == "commonsMedia":
                            media.add(source.target.title())

            for prop, qualifiers in claim.qualifiers.items():
                for qualifier in qualifiers:
                    if qualifier.type == "commonsMedia":
                        media.add(qualifier.target.title())
    return list(media)


def format_commons_media_value(claim):
    """for a commonsMedia claim, format the data value. Use regex to grab the
    description out of a block of text"""
    # NOTE: claim.target.text require a new api call
    text = claim.target.text
    match = re.search("\|[dD]escription={{(.*?)}}\s+\|", text)
    if match:
        description = match.groups()[0]
        match = re.search("([a-z]+)\|[0-9]+=(.*?)$", description)
        if match:
            value = {
                "url": claim.target.full_url(),
                "lang": match[1],
                "label": match[2],
            }
        else:
            value = {"url": claim.target.full_url(), "label": description}
    else:
        match = re.search("\|[dD]escription=(.*?)\s+\|", text)
        if match:
            value = {"url": claim.target.full_url(), "label": match[1]}
        else:

            value = {"url": claim.target.full_url(), "label": claim.target.title()}

    return value


def get_claim_value(claim, ids_dict, include_qid=False):
    """get the value of a claim"""
    if not claim.target:
        return

    if claim.type == "wikibase-item":
        id = claim.target.title()
        label = ids_dict[id]

        if include_qid:
            return id + " " + label
        else:
            return label

    elif claim.type == "wikibase-property":
        id = claim.target.id
        label = ids_dict[id]

        if include_qid:
            return id + " " + label
        else:
            return label

    elif claim.type == "wikibase-lexeme":
        claim_dict = {"labels": {k: v for k, v in claim.target.lemmas.items()}}
        lang = get_claim_language(claim_dict)
        label = claim_dict["labels"][lang]

        return {"label": label, "id": claim.target.id, "url": claim.target.full_url()}

    elif claim.type == "globe-coordinate":
        return {"latitude": claim.target.lat, "longitude": claim.target.lon}

    elif claim.type == "geo-shape":
        url = claim.target.page.full_url() if claim.target.page else None
        return {"label": claim.target.toWikibase(), "url": url}

    elif claim.type == "commonsMedia":
        return claim.target.title()

    elif claim.type == "quantity":
        data = {
            "amount": claim.target.amount.to_eng_string(),
        }
        if claim.target.lowerBound:
            data["lowerBound"] = claim.target.lowerBound.to_eng_string()
        if claim.target.lowerBound:
            data["upperBound"] = claim.target.upperBound.to_eng_string()
        if claim.target.unit != "1":
            # NOTE: claim.target.get_unit_item().labels makes an API request;
            # target.unit does not make API request
            unit_url = claim.target.unit
            id = unit_url.split("/")[-1]
            data["unit"] = ids_dict[id]

        return data

    elif claim.type == "time":
        return claim.target.toTimestr()

    elif claim.type == "monolingualtext":
        return claim.target.text

    else:
        return claim.target


def format_claim_data(claim, prop, id_label_dict, media_metadata):
    """created a nested dictionary for a claim"""
    data = {
        "property": prop,
        "property_value": id_label_dict[prop],
        "data_type": claim.type,
        "data_value": {"value": {}},
    }

    if claim.type == "wikibase-item":
        if claim.target:
            id = claim.target.title()
            data["data_value"]["value"]["label"] = id_label_dict[id]
            data["data_value"]["value"]["id"] = id
            data["data_value"]["value"]["url"] = claim.target.full_url()

    elif claim.type == "wikibase-property":
        if claim.target:
            id = claim.target.id
            data["data_value"]["value"]["label"] = id_label_dict[id]
            data["data_value"]["value"]["id"] = id
            data["data_value"]["value"]["url"] = claim.target.full_url()

    elif claim.type == "commonsMedia":
        if claim.target:
            file_name = claim.target.title()
            data["data_value"]["value"] = media_metadata[file_name]

    else:
        data["data_value"]["value"] = get_claim_value(claim, id_label_dict)

    return data


def create_id_label_dictionary(item, item_json):
    """create dictionary with ids (item Q id and property P id) and their labels"""
    ids = get_ids_for_item(item, item_json, include_pids=True, include_qids=True)

    # connect to wikidata.org API to get labels
    return wq.fetch_and_format_labels_for_ids_sqarql(ids)


def format_display_item_claims(item, item_json, media_metadata):
    """created a nested dictionary for an item claims, references, and
    qualifiers data"""
    id_label_dict = create_id_label_dictionary(item, item_json)

    statements = {}
    identifiers = {}
    for prop, claims in item.claims.items():
        if claims[0].type == "external-id":
            identifiers[prop] = []
        else:
            statements[prop] = []

        for claim in claims:
            claim_data = {
                **format_claim_data(claim, prop, id_label_dict, media_metadata),
                "id": claim.snak,
            }

            if claim.qualifiers:
                claim_data["qualifiers"] = {}

            if claim.sources:
                claim_data["references"] = []

            for prop_q, qualifiers in claim.qualifiers.items():
                claim_data["qualifiers"][prop_q] = []
                for qualifier in qualifiers:
                    qualifier_data = format_claim_data(
                        qualifier, prop_q, id_label_dict, media_metadata
                    )
                    claim_data["qualifiers"][prop_q].append(qualifier_data)

            for source_dict in claim.sources:
                source_dict_data = {}
                for prop_s, sources in source_dict.items():
                    source_dict_data[prop_s] = []
                    for source in sources:
                        source_data = format_claim_data(
                            source, prop_s, id_label_dict, media_metadata
                        )
                        source_dict_data[prop_s].append(source_data)

                claim_data["references"].append(source_dict_data)

            if claims[0].type == "external-id":
                identifiers[prop].append(claim_data)
            else:
                statements[prop].append(claim_data)

    return {"statements": statements, "identifiers": identifiers}


def format_item_field(item_json, type):
    return {lang: values["value"] for lang, values in item_json[type].items()}


def format_item_aliases(item_json):
    data = {}
    for lang, values in item_json["aliases"].items():
        data[lang] = []
        for value in values:

            data[lang].append(value["value"])

    return data


def format_display_item(item, site):
    """takes the json from a item and reshapes it to fit the needs of the
    of our /items/{id} API endpoint
    """
    data = {}
    item_json = item.toJSON()

    for field in ["labels", "descriptions", "aliases"]:
        if field in item_json:
            if field == "aliases":
                data[field] = format_item_aliases(item_json)
            else:
                data[field] = format_item_field(item_json, field)

    # get metadata for every  commons media that is associated with this item
    media_files = get_commons_media_for_item(item)
    media_metadata = wq.fetch_and_format_commons_media_metadata(site, media_files)

    tmp = format_display_item_claims(item, item_json, media_metadata)
    data["statements"] = tmp["statements"]
    data["identifiers"] = tmp["identifiers"]

    return data

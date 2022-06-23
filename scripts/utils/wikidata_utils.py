import pywikibot
from pywikibot.data import api
from datetime import date
from utils.logger import logger
from constants.languages import invalid_languages, allowed_languages


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
            if claim.getTarget() == value:
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
                if old_claim.getTarget() == value:
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


def convert_to_local_claim_value(site, repo, claim, import_sitelinks):
    """When importing claims from wikidata.org, they often refer to items records
    (Q id) that exists in wikidata.org. This method searches if the item record
    exists in the local wikidata. If record exists, return the record
    from local wikidata. If record does not exists, create record in local
    wikidata, and return new record."""
    claim_value = claim.getTarget()

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
        if "en" in unit_dict["labels"]:
            lang = "en"
        else:
            lang = [k for k, v in unit_dict["labels"].items()][0]

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
        if "en" in claim_item_dict["labels"]:
            lang = "en"
        else:
            lang = [k for k, v in claim_item_dict["labels"].items()][0]

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


def get_claim_value(claim, include_qid=True):
    """get the text value of a claim"""
    if claim.type == "wikibase-item":
        if not claim.getTarget():
            return

        labels = claim.getTarget().labels
        languages = [lang for lang in labels]
        label = labels["en"] if "en" in languages else labels[languages[0]]
        if include_qid:
            value = claim.target.title() + " " + label
        else:
            value = label
    elif claim.type == "time":
        value = claim.target.toTimestr()
    elif claim.type == "globe-coordinate":
        value = f"{claim.getTarget().lat} {claim.getTarget().lon}"
    elif claim.type == "quantity":
        value = claim.target.amount.to_eng_string()
    else:
        value = claim.getTarget()

    return value

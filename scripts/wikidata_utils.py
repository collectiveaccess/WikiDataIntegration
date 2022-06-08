import pywikibot
from pywikibot.data import api
from datetime import date


def create_item(site, labels, descriptions=None):
    new_item = pywikibot.ItemPage(site)
    edit_labels(new_item, labels)
    if descriptions:
        edit_descriptions(new_item, descriptions)

    return new_item.getID()


def item_exists(site, label):
    # https://stackoverflow.com/a/45050455
    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "type": "item",
        "search": label,
    }
    api_request = api.Request(site=site, parameters=params)
    result = api_request.submit()

    return process_item_exists_results(result["search"])


def process_item_exists_results(results):
    count = len(results)
    if count == 0:
        return []
    else:
        tmp = []
        for result in results:
            description = result["description"] if "description" in result else None
            tmp.append(
                {
                    "id": result["id"],
                    "label": result["label"],
                    "description": description,
                    "url": result["url"],
                }
            )
        return tmp


def edit_labels(item, new_labels):
    for lang, value in new_labels.items():
        item.editLabels(labels={lang: value}, summary=f"Setting label: {value}")


def edit_descriptions(item, new_descriptions):
    for lang, value in new_descriptions.items():
        item.editDescriptions({lang: value}, summary=f"Setting description: {value}")


def edit_aliases(item, new_alias):
    for lang, value in new_alias.items():
        item.editAliases({lang: value}, summary=f"Set aliases: {value}")


def edit_sitelink(item, site, title):
    sitedict = {"site": site, "title": title}
    item.setSitelink(sitedict, summary=f"Set sitelink: {title}")


def remove_sitelink(item, site):
    item.removeSitelink(site)


def add_statement(repo, item, property, value):
    # return claim if it exists
    if property in item.claims:
        for claim in item.claims[property]:
            if claim.getTarget() == value:
                return claim

    # create new claim
    new_claim = pywikibot.Claim(repo, property)
    new_claim.setTarget(value)
    item.addClaim(new_claim, summary="Add claim.")
    return new_claim


def remove_statement(item, property):
    if property not in item.claims:
        return

    for claim in item.claims[property]:
        item.removeClaims(claim, summary="Remove claim.")


def add_qualifier(repo, claim, property, value):
    # return qualifier if it exists
    if property in claim.qualifiers:
        for qualifier in claim.qualifiers[property]:
            if qualifier.getTarget() == value:
                return qualifier

    # create new qualifier
    new_qualifier = pywikibot.Claim(repo, property)
    new_qualifier.setTarget(value)
    claim.addQualifier(new_qualifier, summary="Add qualifier.")
    return new_qualifier


def remove_qualifier(item, statement_property, qualifier_property):
    if statement_property not in item.claims:
        return

    for claim in item.claims[statement_property]:
        if qualifier_property not in claim.qualifiers:
            continue

        for qualifier in claim.qualifiers[qualifier_property]:
            try:
                claim.removeQualifier(qualifier, summary="Remove qualifier.")
            except:
                print(f"WARNING: could not delete qualifier {qualifier_property}")

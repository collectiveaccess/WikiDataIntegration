import pywikibot
from pywikibot.data import api
from datetime import date


def create_item(site, data):
    repo = site.data_repository()
    new_item = pywikibot.ItemPage(repo)
    edit_entity(new_item, data)
    return new_item


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


def edit_entity(item, data):
    item.editEntity(data, summary=f"Setting label, description, alias, sitelinks")


def edit_aliases(item, new_alias):
    for lang, value in new_alias.items():
        item.editAliases({lang: value}, summary=f"Set aliases: {value}")


def edit_sitelink(item, site, title):
    sitedict = {"site": site, "title": title}
    item.setSitelink(sitedict, summary=f"Set sitelink: {title}")


def remove_sitelink(item, site):
    item.removeSitelink(site)


def add_claim(repo, item, property, value):
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


def remove_claim(item, property):
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


def add_reference(repo, claim, property, value):
    for source in claim.getSources():
        if property in source:
            for old_claim in source[property]:
                if old_claim.getTarget() == value:
                    return old_claim

    new_source = pywikibot.Claim(repo, property)
    new_source.setTarget(value)
    claim.addSources([new_source], summary="Adding sources.")


def add_reference_date(repo, claim, property, source_date=date.today()):
    value = pywikibot.WbTime(
        year=int(source_date.strftime("%Y")),
        month=int(source_date.strftime("%m")),
        day=int(source_date.strftime("%d")),
    )
    add_reference(repo, claim, property, value)


def remove_reference(item, statement_property, reference_property):
    if statement_property not in item.claims:
        return

    sources = []
    for claim in item.claims[statement_property]:
        for old_source in claim.getSources():
            for old_claims in old_source.values():
                for old_claim in old_claims:
                    # import pdb; pdb.set_trace()
                    if old_claim.getID() == reference_property:
                        sources.append(old_claim)

    if len(sources) > 0:
        claim.removeSources(sources, summary="Removed source(s).")


def import_item(site, item_dict, import_sitelinks):
    data = {}
    for key in item_dict.keys():
        if key in ['labels', 'descriptions', 'aliases']:
            if len(item_dict[key]) > 0:
                data[key] = {k: v for k, v in item_dict[key].items()}
        elif key == 'sitelinks':
            if import_sitelinks and len(item_dict[key]) > 0:
                data[key] = [{k: v.title} for k, v in item_dict[key].items()]
        elif key == 'claims':
            continue
        else:
            print(f'{key} not imported')

    return create_item(site, data)

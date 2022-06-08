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

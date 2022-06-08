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

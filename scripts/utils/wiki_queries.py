import requests
import json

WIKI_BASE_URL = "https://www.wikidata.org"
WIKI_QUERY_URL = "https://query.wikidata.org/sparql"


def wikidata_query(query):
    # https://stackoverflow.com/a/66223213
    try:
        response = requests.get(
            WIKI_QUERY_URL, params={"format": "json", "query": query}
        )
        return response.json()["results"]["bindings"]
    except json.JSONDecodeError as e:
        raise Exception("Invalid query", e)


def process_wikidata_properties(results):
    data = {}
    for result in results:
        pid = result["property"]["value"].split("/")[-1]
        value = result["propertyLabel"]["value"]
        data[pid] = value

    return data

    return data


def fetch_all_properties():
    """
    get all properties from wikidata

    https://stackoverflow.com/questions/25100224/how-to-get-a-list-of-all-wikidata-properties
    """

    query = """
    SELECT ?property ?propertyLabel WHERE {
        ?property a wikibase:Property .

        SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
    }
    """

    results = wikidata_query(query)
    return process_wikidata_properties(results)


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
        link = (
            f"{WIKI_BASE_URL}/w/api.php?action=wbgetentities"
            f"&ids={ids_str}&props=labels&languages={lang}&format=json"
        )
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

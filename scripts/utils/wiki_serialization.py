import re

from scripts.utils.logger import logger


def get_claim_language(claim_dict):
    if "en" in claim_dict["labels"]:
        lang = "en"
    else:
        lang = [k for k, v in claim_dict["labels"].items()][0]

    return lang


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


def get_claim_label(claim, ids_dict, include_qid=False):
    """get the label info that shown on the site for a claim"""
    if not claim.target:
        return

    if claim.type == "wikibase-item":
        id = claim.target.id
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


def format_claim_data(claim, prop, id_label_dict, media_metadata, external_id_links):
    """created a nested dictionary for a claim"""
    # common attributes for each claim
    data = {
        "property": prop,
        "property_value": id_label_dict[prop],
        "data_type": claim.type,
        "data_value": {"value": {}},
    }

    # set ['data_value']['value'] based on claim type
    if claim.type == "wikibase-item":
        if claim.target:
            id = claim.target.title().replace('Item:', '')
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

    elif claim.type == "external-id":
        url = external_id_links[prop] if prop in external_id_links else None
        data["data_value"]["value"]["label"] = get_claim_label(claim, id_label_dict)
        data["data_value"]["value"]["url"] = url

    else:
        data["data_value"]["value"] = get_claim_label(claim, id_label_dict)

    return data


def format_item_claims(item, id_label_dict, media_metadata, external_id_links):
    """created a nested dictionary for an item's claims, references, and
    qualifiers"""
    statements = {}
    identifiers = {}
    for prop, claims in item.claims.items():
        # separate claims into identifiers and statements
        if claims[0].type == "external-id":
            identifiers[prop] = []
        else:
            statements[prop] = []

        for claim in claims:
            # process the main claim
            claim_data = {
                **format_claim_data(
                    claim, prop, id_label_dict, media_metadata, external_id_links
                ),
                "id": claim.snak,
            }

            # process qualifiers for a claim
            if claim.qualifiers:
                claim_data["qualifiers"] = {}
            for prop_q, qualifiers in claim.qualifiers.items():
                claim_data["qualifiers"][prop_q] = []
                for qualifier in qualifiers:
                    qualifier_data = format_claim_data(
                        qualifier,
                        prop_q,
                        id_label_dict,
                        media_metadata,
                        external_id_links,
                    )
                    claim_data["qualifiers"][prop_q].append(qualifier_data)

            # process references for a claim
            if claim.sources:
                claim_data["references"] = []
            for source_dict in claim.sources:
                source_dict_data = {}
                for prop_s, sources in source_dict.items():
                    source_dict_data[prop_s] = []
                    for source in sources:
                        source_data = format_claim_data(
                            source,
                            prop_s,
                            id_label_dict,
                            media_metadata,
                            external_id_links,
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

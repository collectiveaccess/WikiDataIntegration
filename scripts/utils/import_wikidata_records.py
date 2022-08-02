import pywikibot

import scripts.utils.wikidata_utils as wd
from scripts.utils.logger import logger
import scripts.utils.wiki_queries as wq
import scripts.utils.wiki_serialization as ws


def find_or_create_local_item(item_dict, local_site, local_repo):
    lang = ws.get_claim_language(item_dict)
    label = item_dict["labels"][lang]
    description = item_dict["descriptions"][lang]

    # check if item exists locally
    existing = False
    existing_id = None
    results = wq.search_keyword(local_site, label, lang)
    for result in results:
        # if no description, check if any of the existing records have same
        # label as the current row
        if not description:
            if result["label"] == label:
                existing = True
                existing_id = result["id"]

        # check if any of the existing records have same description and
        # label as current row
        elif "label" in result and result["label"]:
            if result["description"] == description and result["label"] == label:
                existing = True
                existing_id = result["id"]

    # get existing item
    if existing:
        item = pywikibot.ItemPage(local_repo, existing_id)
    # create new item
    else:
        item = wd.import_item(local_site, item_dict, import_sitelinks=False)

    return item


def add_statements_to_local_item(item_dict, repo, local_item, local_site, local_repo):
    pywikibot.config.put_throttle = 1

    # iterate over all the wikidata.org claims
    for property, values in item_dict["claims"].items():
        for claim in values:

            new_claim_value = wd.convert_to_local_claim_value(
                local_site, local_repo, claim, import_sitelinks=False
            )
            if new_claim_value:
                wd.add_claim(repo, local_item, property, new_claim_value)


def add_qualifier_to_wikidata_claim(
    claim, local_claim, local_site, local_repo, site, repo, import_sitelinks
):
    # claim.qualifiers returns an ordered dictionary
    for qualifier_property, qualifier_claims in claim.qualifiers.items():

        for qualifier_claim in qualifier_claims:
            qualifier_value = wd.convert_to_local_claim_value(
                local_site,
                local_repo,
                qualifier_claim,
                import_sitelinks,
            )

            # check is source exists locally
            exists = False
            if qualifier_property in local_claim.qualifiers:
                for l_source in local_claim.qualifiers[qualifier_property]:
                    if l_source.getTarget() == qualifier_value:
                        exists = True

            # add new source claim
            if not exists:
                try:
                    new_claim = pywikibot.Claim(repo, qualifier_property)
                    new_claim.setTarget(qualifier_value)
                    local_claim.addQualifier(new_claim, summary="Add qualifier.")
                    logger.info(
                        f"Add qualifier: {claim.id} "
                        f"{qualifier_property} {qualifier_value}"
                    )
                except:
                    logger.error(
                        f"Qualifier not added: {claim.id} "
                        f"{qualifier_property} {qualifier_value}"
                    )


def add_source_to_wikidata_claim(
    claim, local_claim, local_site, local_repo, site, repo, import_sitelinks
):
    # claim.sources returns a list or ordered dictionariers
    for claim_source in claim.sources:
        new_sources = []
        for source_property, source_values in claim_source.items():

            # NOTE:skip P4656 "Wikimedia import URL"
            # since we don't have wikipedia pages.
            # https://phabricator.wikimedia.org/T301243
            if source_property in ["P4656"]:
                continue
            # NOTE: skip reference url since there is a bug with saving URL
            if source_property in ["P854"]:
                continue

            for source_claim in source_values:
                source_value = wd.convert_to_local_claim_value(
                    local_site,
                    local_repo,
                    source_claim,
                    import_sitelinks,
                )

                # check is source exists locally
                exists = False
                for l_source in local_claim.sources:
                    if source_property in l_source.keys():
                        for ll_source in l_source[source_property]:
                            if ll_source.getTarget() == source_value:
                                exists = True

                # add new source claim
                if not exists:
                    try:
                        new_source = pywikibot.Claim(repo, source_property)
                        new_source.setTarget(source_value)
                    except:
                        print("new_source target", source_property)
                    new_sources.append(new_source)

        if len(new_sources) > 0:
            try:
                local_claim.addSources(new_sources, summary="Adding sources.")
                logger.info(f"Sources added: {local_claim.id}")
            except:
                logger.error(f"Sources not saved: {local_claim.id}")


def create_local_id_label_dictionary(local_item):
    # can't use sparql to get labels for local wikibase qid because I can't
    # get sparql working. use api call to local wikibase to get labels.
    # api call doesn't work on federated properties.
    qids = wd.get_ids_for_item(
        local_item, local_item.toJSON(), include_pids=False, include_qids=True
    )
    qid_dict = wq.fetch_and_format_labels_for_ids(qids, "http://whirl.mine.nu:8888")

    # use sparql query to wikidata.org to get pids
    pids = wd.get_ids_for_item(
        local_item, local_item.toJSON(), include_pids=True, include_qids=False
    )
    pid_dict = wq.fetch_and_format_labels_for_ids_sqarql(pids)

    return {**qid_dict, **pid_dict}


def add_sources_and_qualifiers_to_local_item(
    item_dict,
    id_label_dict,
    site,
    repo,
    local_item,
    local_id_label_dict,
    local_site,
    local_repo,
):
    pywikibot.config.put_throttle = 1

    # iterate over all the wikidata.org claims
    for property, claims in item_dict["claims"].items():
        for claim in claims:
            # skip commonsMedia claims since we don't import them
            if claim.type == "commonsMedia":
                continue

            # get the corresponding local claim
            if claim.id in local_item.claims:
                for l_claim in local_item.claims[claim.id]:
                    if ws.get_claim_label(
                        l_claim, local_id_label_dict, False
                    ) == ws.get_claim_label(claim, id_label_dict, False):
                        local_claim = l_claim

            try:
                add_source_to_wikidata_claim(
                    claim,
                    local_claim,
                    local_site,
                    local_repo,
                    site,
                    repo,
                    import_sitelinks=False,
                )
            except:
                logger.error(f"{claim.id} source not added")

            try:
                add_qualifier_to_wikidata_claim(
                    claim,
                    local_claim,
                    local_site,
                    local_repo,
                    site,
                    repo,
                    import_sitelinks=False,
                )
            except:
                logger.error(f"{claim.id} qualifier not added")


def import_wikidata_item_to_local_wikibase(qid, site, local_site):
    pywikibot.config.put_throttle = 1
    local_repo = local_site.data_repository()

    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, qid)
    item_dict = item.get()

    local_item = find_or_create_local_item(item_dict, local_site, local_repo)

    print('add statements begin...')
    add_statements_to_local_item(item_dict, repo, local_item, local_site, local_repo)
    id_label_dict = wd.create_id_label_dictionary(item, item.toJSON())
    local_id_label_dict = create_local_id_label_dictionary(local_item)
    print('add statements end...')

    # reload item after adding statements, then add sources/qualifiers
    local_item = find_or_create_local_item(item_dict, local_site, local_repo)

    print('add souces / qualifiers begin...')
    add_sources_and_qualifiers_to_local_item(
        item_dict,
        id_label_dict,
        site,
        repo,
        local_item,
        local_id_label_dict,
        local_site,
        local_repo,
    )
    print('add souces / qualifiers end...')

    lang = wd.get_claim_language(item_dict)
    label = item_dict["labels"][lang]
    return {"id": local_item.id, "label": label}

import pywikibot
import utils.wikidata_utils as wd
from constants.wd_properties import properties

"""Edit claims for item Q225211 in test.wikidata.org """

site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

local_site = pywikibot.Site("en", "cawiki")
local_repo = local_site.data_repository()
local_item = pywikibot.ItemPage(local_repo, "Q592")
local_item_dict = local_item.get()

url_prop = properties["reference URL"]
fast_prop = properties["FAST ID"]
sex_prop = properties["sex or gender"]


for property, claims in local_item_dict["claims"].items():
    if property == sex_prop:
        for claim in claims:
            wd.add_reference(repo, claim, fast_prop, "456")
            wd.add_reference(repo, claim, url_prop, "http://example.com")

            new_source = pywikibot.Claim(repo, url_prop)
            new_source.setTarget("http://example.org")
            claim.addSources([new_source], summary="Adding sources.")

import pywikibot
import utils.wikidata_utils as wd

"""Edit claims for item Q225211 in test.wikidata.org """

site = pywikibot.Site("test", "wikidata")
repo = site.data_repository()

# label = "foo"
# data = {"labels": {"en": label}, "descriptions": {"en": "description"}}
# wd.create_item(site, data)

data = {"labels": {"en": 'foobar 1234'}, "descriptions": {"en": 'foobar 1234'}}
wd.import_item(site, data)

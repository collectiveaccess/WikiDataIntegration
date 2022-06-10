import pywikibot
import utils.wikidata_utils as wd


site = pywikibot.Site("test", "wikidata")
repo = site.data_repository()
item = pywikibot.ItemPage(repo, "Q225211")

print(item)

new_labels = {"en": "foobar"}
wd.edit_labels(item, new_labels)

new_descr = {"en": "short description text"}
wd.edit_descriptions(item, new_descr)

new_alias = {"en": ["foobar 1", "foobar 2", "foobar 3"]}
wd.edit_aliases(item, new_alias)

wd.edit_sitelink(item, "enwiki", "Jane Austen")
# remove_sitelink(item, 'enwiki')

import pywikibot
import utils.wikidata_utils as wd

"""search test.wikidata.org by keywords"""

site = pywikibot.Site("test", "wikidata")

keywords = ["foo", "foo2", "foo 06-07 1"]

for keyword in keywords:
    res = wd.item_exists(site, keyword)
    if len(res) == 0:
        print(f"{keyword}: zero items found")
    elif len(res) == 1:
        print(f"{keyword}: one item found")
        print(res[0])
    else:
        print(f"{keyword}: multiple items found")
        for r in res:
            print(r)
    print()

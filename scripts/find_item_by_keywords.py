import pywikibot
import utils.wikidata_utils as wd

"""search test.wikidata.org by keywords"""

site = pywikibot.Site("test", "wikidata")

keywords = ["foo", "foo2", "foo 06-07 1"]

for keyword in keywords:
    print(keyword)
    res = wd.item_exists(site, keyword)
    if len(res) == 0:
        print(f"will create item: {keyword}")
    elif len(res) == 1:
        print("one item found", res[0]["id"])
    else:
        print("multiple items found", res)
    print()

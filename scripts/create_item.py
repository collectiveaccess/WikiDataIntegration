import pywikibot
import utils.wikidata_utils as wd

site = pywikibot.Site("test", "wikidata")

labels = ["foo", "foo2", "foo 06-07 1"]
label = labels[0]

res = wd.item_exists(site, label)
if len(res) == 0:
    print(f"will create item: {label}")
    # wd.create_item(site, {"en": label})
elif len(res) == 1:
    print("one item found", res[0]["id"])
else:
    print("multiple items found", res)

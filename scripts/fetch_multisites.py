import pywikibot

"""fetch item from wikidata.org, test.wikidata.org, whirl.mine.nu:8888"""


def display_item(site, qid):
    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, qid)
    item_dict = item.get()

    print("---")
    print(site)
    print()
    print(item_dict["labels"]["en"])
    print()
    print(item_dict["descriptions"]["en"])


site = pywikibot.Site("wikidata", "wikidata")
display_item(site, "Q1")

site = pywikibot.Site("en", "cawiki")
display_item(site, "Q1")

site = pywikibot.Site("test", "wikidata")
display_item(site, "Q250")

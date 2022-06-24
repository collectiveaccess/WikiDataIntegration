import pywikibot

"""display item Q225211 in test.wikidata.org"""

site = pywikibot.Site("test", "wikidata")
repo = site.data_repository()
item = pywikibot.ItemPage(repo, "Q225211")

item_dict = item.get()

for key in item_dict.keys():
    print("----")
    if key == "claims":
        print("claims: ")
        for property, values in item_dict["claims"].items():
            print(">>>")
            print("property: ", property)
            for claim in values:
                claim_value = claim.target
                print(claim_value)
    else:
        print(f"{key}: ", item_dict[key])

import pywikibot
import utils.wikidata_utils as wd
from datetime import date
from constants.wd_properties import test_properties

"""Edit claims for item Q225211 in test.wikidata.org """

site = pywikibot.Site("test", "wikidata")
repo = site.data_repository()
item = pywikibot.ItemPage(repo, "Q225211")
item.get()

api_prop = test_properties["API endpoint"]
wd_item_prop = test_properties["corresponds with WD item"]
gov_prop = test_properties["basic form of government"]
retrieved_prop = test_properties["date retrieved"]
coor_prop = test_properties["Test coordinate"]
birthday_prop = test_properties["date of birth2"]
domain_prop = test_properties["top-level domainn"]
stated_prop = test_properties["stated in"]


# add claim with string value
wd.add_claim(repo, item, api_prop, "abc")

# add claim with coordinates value
value = pywikibot.Coordinate(site=repo, lat=52.90, lon=0.1225, precision=0.001)
wd.add_claim(repo, item, coor_prop, value)

# add claim with date value
value = pywikibot.WbTime(site=repo, year=1999, month=6, day=8)
wd.add_claim(repo, item, birthday_prop, value)

# add claim with item value
value = pywikibot.ItemPage(repo, "Q4546")
wd.add_claim(repo, item, gov_prop, value)

# add and remove claim
wd.add_claim(repo, item, wd_item_prop, "xyz")
wd.remove_claim(item, wd_item_prop)

# add claim with item value
value = pywikibot.ItemPage(repo, "Q350")
statement = wd.add_claim(repo, item, gov_prop, value)
# add qualifier to claim
value = pywikibot.ItemPage(repo, "Q35408")
wd.add_qualifier(repo, statement, domain_prop, value)
# add and remove qualifier
wd.add_qualifier(repo, statement, wd_item_prop, "def")
wd.remove_qualifier(item, gov_prop, wd_item_prop)
# add references to claim
value = pywikibot.ItemPage(repo, "Q202473")
wd.add_reference(repo, statement, stated_prop, value)
wd.add_reference_date(repo, statement, retrieved_prop)
wd.add_reference_date(repo, statement, retrieved_prop, date(2022, 1, 9))
# add and remove references
wd.add_reference(repo, statement, wd_item_prop, "aaa")
wd.add_reference(repo, statement, wd_item_prop, "bbb")
wd.remove_reference(item, gov_prop, wd_item_prop)

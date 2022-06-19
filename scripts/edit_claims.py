import pywikibot
import utils.wikidata_utils as wd
from datetime import date

"""Edit claims for item Q225211 in test.wikidata.org """

site = pywikibot.Site("test", "wikidata")
repo = site.data_repository()
item = pywikibot.ItemPage(repo, "Q225211")
item.get()

# add claim with string value
wd.add_claim(repo, item, "P345", "abc")

# add claim with coordinates value
value = pywikibot.Coordinate(site=repo, lat=52.90, lon=0.1225, precision=0.001)
wd.add_claim(repo, item, "P35", value)

# add claim with date value
value = pywikibot.WbTime(site=repo, year=1999, month=6, day=8)
wd.add_claim(repo, item, "P95197", value)

# add claim with item value
value = pywikibot.ItemPage(repo, "Q4546")
wd.add_claim(repo, item, "P131", value)

# add and remove claim
wd.add_claim(repo, item, "P207", "xyz")
wd.remove_claim(item, "P207")

# add claim with item value
value = pywikibot.ItemPage(repo, "Q350")
statement = wd.add_claim(repo, item, "P131", value)
# add qualifier to claim
value = pywikibot.ItemPage(repo, "Q35408")
wd.add_qualifier(repo, statement, "P100", value)
# add and remove qualifier
wd.add_qualifier(repo, statement, "P207", "def")
wd.remove_qualifier(item, "P131", "P207")
# add references to claim
value = pywikibot.ItemPage(repo, "Q202473")
wd.add_reference(repo, statement, "P149", value)
wd.add_reference_date(repo, statement, "P146")
wd.add_reference_date(repo, statement, "P146", date(2022, 1, 9))
# add and remove references
wd.add_reference(repo, statement, "P207", "aaa")
wd.add_reference(repo, statement, "P207", "bbb")
wd.remove_reference(item, "P131", "P207")

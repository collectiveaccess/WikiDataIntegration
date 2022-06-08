import pywikibot
import wikidata_utils as wd
from datetime import date


site = pywikibot.Site("test", "wikidata")
repo = site.data_repository()
item = pywikibot.ItemPage(repo, "Q225211")
item.get()

# string value
wd.add_statement(repo, item, "P345", "abc")

# coordinates value
value = pywikibot.Coordinate(lat=52.208, lon=0.1225, precision=0.001)
wd.add_statement(repo, item, "P35", value)

# date value
value = pywikibot.WbTime(year=1977, month=6, day=8)
wd.add_statement(repo, item, "P95197", value)

# item value
value = pywikibot.ItemPage(repo, "Q4546")
wd.add_statement(repo, item, "P131", value)

# add and remove statement
wd.add_statement(repo, item, "P207", "xyz")
wd.remove_statement(item, "P207")

# item value
value = pywikibot.ItemPage(repo, "Q350")
statement = wd.add_statement(repo, item, "P131", value)
# add qualifier
value = pywikibot.ItemPage(repo, "Q35408")
wd.add_qualifier(repo, statement, "P100", value)
# add and remove qualifier
wd.add_qualifier(repo, statement, "P207", "def")
wd.remove_qualifier(item, "P131", "P207")
# add references
value = pywikibot.ItemPage(repo, "Q202473")
wd.add_reference(repo, statement, "P149", value)
wd.add_reference_date(repo, statement, "P146")
wd.add_reference_date(repo, statement, "P146", date(2022, 1, 9))
# add and remove references
wd.add_reference(repo, statement, "P207", "aaa")
wd.add_reference(repo, statement, "P207", "bbb")
wd.remove_reference(item, "P131", "P207")

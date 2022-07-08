import sys
from pathlib import Path
import pywikibot

parent_path = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_path))


import utils.wiki_queries as wd

site = pywikibot.Site("wikidata", "wikidata")
results = wd.search_keyword(site, 'Earth')
print(results)

print('\n', '-----', '\n')

repo = site.data_repository()
item = pywikibot.ItemPage(repo, "Q2")
print(item.labels)

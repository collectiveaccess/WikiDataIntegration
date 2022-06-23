from fastapi import FastAPI, HTTPException
import sys
from pathlib import Path
import pywikibot
import re

project_path = Path(__file__).resolve().parent.parent
sys.path.append(str(project_path))
sys.path.append(str(project_path / "scripts"))

import scripts.utils.wikidata_utils as wd


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id):
    # check for invalid item_id
    if not re.search(r"^Q[0-9]+$", item_id):
        raise HTTPException(status_code=404, detail="Item not found")

    site = pywikibot.Site("test", "wikidata")
    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, item_id)

    if item.exists():
        results = wd.format_display_item(item)
    else:
        raise HTTPException(status_code=404, detail="Item not found")

    return results


@app.get("/search")
def read_search(keyword=None):
    site = pywikibot.Site("wikidata", "wikidata")
    if keyword:
        result = wd.item_exists(site, keyword)
    else:
        result = []

    return result

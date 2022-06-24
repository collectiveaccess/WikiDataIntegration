import sys
from pathlib import Path
import re
import json

import pywikibot
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

project_path = Path(__file__).resolve().parent.parent
sys.path.append(str(project_path))
sys.path.append(str(project_path / "scripts"))

import scripts.utils.wikidata_utils as wd

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# need to set headers to ensure we are using utf-8
headers = {"Content-Type": "application/json;charset=UTF-8", "Charset": "utf-8"}


@app.get("/")
def read_root():
    content = {"Hello": "World", "message": "塔当"}
    return JSONResponse(content=content, headers=headers)


@app.get("/items/{item_id}")
def read_item(item_id):
    # check for invalid item_id
    if not re.search(r"^Q[0-9]+$", item_id):
        raise HTTPException(status_code=404, detail="Item not found")

    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, item_id)

    if item.exists():
        content = wd.format_display_item(item)
        try:
            json.dumps(content)
        except TypeError as err:
            content = {"error": err.args[0]}
    else:
        raise HTTPException(status_code=404, detail="Item not found")

    return JSONResponse(content=content, headers=headers)


@app.get("/search")
def read_search(keyword=None):
    site = pywikibot.Site("wikidata", "wikidata")
    if keyword:
        results = wd.item_exists(site, keyword)

        content = []
        for res in results:
            if res["description"]:
                content.append(
                    {"id": res["id"], "label": f"{res['label']} ({res['description']})"}
                )
            else:
                content.append({"id": res["id"], "label": f"{res['label']}"})

    else:
        content = []

    return JSONResponse(content=content, headers=headers)

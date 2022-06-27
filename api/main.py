import sys
from pathlib import Path
import re
import json

import pywikibot
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

project_path = Path(__file__).resolve().parent.parent
sys.path.append(str(project_path))
sys.path.append(str(project_path / "scripts"))

import scripts.utils.wikidata_utils as wd  # noqa: E402
import scripts.utils.wiki_queries as wq  # noqa: E402

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
    content = {"message_1": "Hello", "message_2": "你好"}
    return JSONResponse(content=content, headers=headers)


@app.get("/items/{item_id}")
def read_item(item_id: str):
    # check for invalid item_id
    if not re.search(r"^Q[0-9]+$", item_id):
        raise HTTPException(status_code=404, detail="Item not found")

    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
    item = pywikibot.ItemPage(repo, item_id)

    if item.exists():
        content = wd.format_display_item(item, site)
        try:
            json.dumps(content)
        except TypeError as err:
            content = {"error": err.args[0]}
    else:
        raise HTTPException(status_code=404, detail="Item not found")

    return JSONResponse(content=content, headers=headers)


@app.get("/search")
def read_search(keyword: str):
    site = pywikibot.Site("wikidata", "wikidata")
    if keyword:
        results = wq.search_keyword(site, keyword)

        content = []
        for res in results:
            data = {
                "id": res["id"],
                "label": res["label"],
            }
            label = res["label"]
            if res["description"]:
                label += f" ({res['description']})"
            data["search_label"] = label

            content.append(data)
    else:
        content = []

    return JSONResponse(content=content, headers=headers)


class WikidataItem(BaseModel):
    item_id: str
    item_label: str
    item_data: dict


def read_data_json(f, emptyFileResponse):
    try:
        return json.load(f)
    except json.decoder.JSONDecodeError as err:
        # file has no content
        if err.msg == "Expecting value":
            return emptyFileResponse
        else:
            raise HTTPException(status_code=500, detail=err.msg)


def save_item(data):
    # TODO: update save functionality
    filepath = project_path / "data" / "wiki_imports.json"

    with open(filepath, "r") as f:
        records = read_data_json(f, {})

    records[data.item_id] = {
        "id": data.item_id,
        "label": data.item_label,
        "data": data.item_data,
    }

    with open(filepath, "w") as f:
        json_object = json.dumps(records, indent=2)
        f.write(json_object)


@app.post("/import_wikidata")
def import_wikidata(data: WikidataItem):
    save_item(data)

    content = {"message": f"record imported: {data.item_id} {data.item_label}"}
    return JSONResponse(content=content, headers=headers)


@app.get("/items")
def read_all_items():
    filepath = project_path / "data" / "wiki_imports.json"

    with open(filepath, "r") as f:
        records = read_data_json(f, [])
        if len(records) > 0:
            content = [
                {"id": values["id"], "label": values["label"]}
                for values in records.values()
            ]
        else:
            content = []

    return JSONResponse(content=content, headers=headers)

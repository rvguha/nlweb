from pymilvus import MilvusClient
import mllm
import json

milvus_client_prod = None

def initialize():
    global milvus_client_prod
    print("initializing milvus client")
    milvus_client_prod = MilvusClient("../milvus/milvus_prod.db")
    search_db("test", "all", 10)

def search_db(query, site, num_results=50):
    if (milvus_client_prod is None):
        initialize()
    print(f"retrieval query: {query}, site: {site}")
    embedding = mllm.get_embedding(query)
    client = milvus_client_prod 
    if (site == "bc_product"):
        site = "backcountry"
    if (site == "npr podcasts"):
        site = ["npr podcasts", "med podcast"]
    if (site == "nlws"):
        site = "all"
    if (site == "all"):
        res = client.search(
            collection_name="prod_collection",
            data=[embedding],
            limit=num_results,
            output_fields=["url", "text", "name", "site"],
        )
    elif isinstance(site, list):
        site_filter = " || ".join([f"site == '{s}'" for s in site])
        res = client.search(
            collection_name="prod_collection", 
            data=[embedding],
            filter=site_filter,
            limit=num_results,
            output_fields=["url", "text", "name", "site"],
        )
    else:
        res = client.search(
            collection_name="prod_collection",
            data=[embedding],
            filter=f"site == '{site}'",
            limit=num_results,
            output_fields=["url", "text", "name", "site"],
        )

    retval = []
    for item in res[0]:
        ent = item["entity"]
        txt = json.dumps(ent["text"])
        retval.append([ent["url"], txt, ent["name"], ent["site"]])
    print(f"Retrieved {len(retval)} items")
    return retval

def retrieve_item_with_url(url):
    client = milvus_client_prod 
    print(f"Querying for '{url}'")
    res = client.query(
        collection_name="prod_collection",
    #    data=[embedding],
        filter=f"url == '{url}'",
        limit=1,
        output_fields=["url", "text", "name", "site"],
    )
  #  print(f"Retrieved {res}")
    if (len(res) == 0):
        return None
    return res[0]

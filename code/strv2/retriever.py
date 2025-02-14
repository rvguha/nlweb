from pymilvus import MilvusClient
import mllm
milvus_client_prod = MilvusClient("./milvus_prod.db")


def search_db(query, site, num_results=50):
    print(f"query: {query}, site: {site}")
    embedding = mllm.get_embedding(query)
    client = milvus_client_prod 
    if (site == "imdb2"):
        site = "imdb"
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
        retval.append([ent["url"], ent["text"], ent["name"], ent["site"]])
    print(f"Retrieved {len(retval)} items")
    return retval

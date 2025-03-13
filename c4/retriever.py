from pymilvus import MilvusClient
import mllm

async def initialize():
    global milvus_client_prod
    milvus_client_prod = MilvusClient("../milvus/milvus_prod.db")
    await MilvusQueryRetriever(None).search_db("test", "all", 10)

class MilvusQueryRetriever:
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        results = await self.search_db(self.handler.query, self.handler.site, 50)
        self.handler.retrieved_items = results
        return results


    async def search_db(self, query, site, num_results=50):
        print(f"query: {query}, site: {site}")
        embedding = mllm.get_embedding(query)
        client = milvus_client_prod 
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
            retval.append([ent["url"], ent["text"], ent["name"], ent["site"]])
        print(f"Retrieved {len(retval)} items")
        return retval

class MilvusItemRetriever:
    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        results = await self.retrieve_item_with_url(self.handler.context_url)
        self.handler.context_item = results
        

    async def retrieve_item_with_url(url):
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

import milvus_retrieve
import azure_retrieve
import mllm
import time
import milvus_retrieve


class DBQueryRetriever:
    def __init__(self, query, handler, db_type="azure_ai_search"):
        self.db_query = query
        self.handler = handler
        self.db_type = db_type

    async def search_db(self, query, site, num_results=50):
        start_time = time.time()
        site = site.replace(" ", "_")
        print(f"retrieval query: {query}, site: '{site}', db: {self.db_type}")
        if (self.db_type == "milvus"):
            results = milvus_retrieve.search_db(query, site, num_results)
        elif (self.db_type == "azure_ai_search"):
            if site == "all" or site == "nlws":
                results = await azure_retrieve.search_all_sites(query, num_results)
            else:
                results = await azure_retrieve.search_db(query, site, num_results)
        else:
            raise ValueError(f"Invalid database: {self.db_type}")
        end_time = time.time()
        print(f"Search took {end_time - start_time:.2f} seconds")
        return results

    async def do(self):
        results = await self.search_db(self.db_query, self.handler.site, 50)
        self.handler.retrieved_items = results
        self.handler.state.retrieval_done = True
        return results

class DBItemRetriever:
    def __init__(self, handler, db_type="azure_ai_search"):
        self.handler = handler
        self.db_type = db_type

    async def do(self):
        results = await self.retrieve_item_with_url(self.handler.context_url)
        self.handler.context_item = results
        
    def retrieve_item_with_url(self, url):
        if (self.db_type == "milvus"):
            return milvus_retrieve.retrieve_item_with_url(url)
        elif (self.db_type == "azure_ai_search"):
            return azure_retrieve.retrieve_item_with_url(url)
        else:
            raise ValueError(f"Invalid database: {self.db_type}")

  
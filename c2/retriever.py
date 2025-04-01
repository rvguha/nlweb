import milvus_retrieve
import azure_retrieve
import mllm

def initialize():
    return

def search_db(query, site, num_results=50, db="azure_ai_search"):
    print(f"retrieval query: {query}, site: {site}, db: {db}")
    if (db == "milvus"):
        return milvus_retrieve.search_db(query, site, num_results)
    elif (db == "azure_ai_search"):
        return azure_retrieve.search_db(query, site, num_results)
    else:
        raise ValueError(f"Invalid database: {db}")
    
def retrieve_item_with_url(url):
    if (db == "milvus"):
        return milvus_retrieve.retrieve_item_with_url(url)
    elif (db == "azure_ai_search"):
        return azure_retrieve.retrieve_item_with_url(url)
    else:
        raise ValueError(f"Invalid database: {db}")

import milvus_retrieve
import azure_retrieve
import mllm

def initialize():
    return

def search_db(query, site, num_results=50, db="azure_ai_search"):
    import time
    start_time = time.time()
    site = site.replace(" ", "_")
    print(f"retrieval query: {query}, site: '{site}', db: {db}")
    if (db == "milvus"):
        results = milvus_retrieve.search_db(query, site, num_results)
    elif (db == "azure_ai_search"):
        if site == "all" or site == "nlws":
            results = azure_retrieve.search_all_sites(query, num_results)
        elif site == "bc_product":
            site = "backcountry"
            results = azure_retrieve.search_db(query, site, num_results)
        else:
            results = azure_retrieve.search_db(query, site, num_results)
    else:
        raise ValueError(f"Invalid database: {db}")
    end_time = time.time()
    print(f"Search took {end_time - start_time:.2f} seconds")
    return results
    
def retrieve_item_with_url(url, db="azure_ai_search"):
    if (db == "milvus"):
        return milvus_retrieve.retrieve_item_with_url(url)
    elif (db == "azure_ai_search"):
        return azure_retrieve.retrieve_item_with_url(url)
    else:
        raise ValueError(f"Invalid database: {db}")

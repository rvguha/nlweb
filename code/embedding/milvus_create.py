from pymilvus import MilvusClient, Collection, utility
import numpy as np
#import retrieval
import json
import os

skipTypes = ["ItemList", "ListItem", "AboutPage", "WebPage", "WebSite", "Organization", "Person"]

includeTypes = ["Recipe", "NeurIPSPoster", "InvitedTalk", "Oral", "Movie", 
                "TVShow", "TVEpisode", "Product", "Offer", "PodcastEpisode", 
                "Podcast", "TVSeries", "ProductGroup", "Event", "FoodEstablishment",
                "Apartment", "House", "Home", "RealEstateListing","SingleFamilyResidence", "Offer"] 
              

EMBEDDINGS_PATH_SMALL = "/Users/guha/mahi/data/sites/embeddings/small/"
EMBEDDINGS_PATH_LARGE = "/Users/guha/mahi/data/sites/embeddings/large/"

EMBEDDING_SIZE = "small"

def int64_hash(string):
    # Compute the hash
    hash_value = hash(string)
    # Ensure it fits within int64 range
    return np.int64(hash_value)

# Example usage

def create_db(embedding_size=EMBEDDING_SIZE, first_drop=False):
    if (embedding_size == "small"):
        size = 1536
    else:
        size = 3072
    if (first_drop and client.has_collection("prod_collection")):
        client.drop_collection("prod_collection")
    if (not client.has_collection("prod_collection")):
        client.create_collection(
            collection_name="prod_collection",
            dimension=size  
        )

def includeItem(js):
    if "@type" in js:
        item_type = js["@type"]
        if isinstance(item_type, list):
            if any(t in includeTypes for t in item_type):
                return True
        if item_type in includeTypes:
            return True
    elif "@graph" in js:
        for item in js["@graph"]:
            if includeItem(item):
                return True

    return False

def getName(js):
    nameFields = ["name", "headline", "title", "keywords"]
    for field in nameFields:
        if (field in js):
            return js[field]
    if ("url" in js):
        url = js["url"]
    elif ("@id" in js):
        url = js["@id"  ]
    else:
        return ""
    # Remove site name and split by '/'
    parts = url.replace('https://', '').replace('http://', '').split('/', 1)
    if len(parts) > 1:
        path = parts[1]
        # Get longest part when split by '/'
        path_parts = path.split('/')
        longest_part = max(path_parts, key=len)
        # Replace hyphens with spaces and capitalize words
        name = ' '.join(word.capitalize() for word in longest_part.replace('-', ' ').split())
        return name
    return ""

def normalize_list(js):
    retval = []
    if isinstance(js, list):
        for item in js:
            if (isinstance(item, list) and len(item) == 1):
                item = item[0]
            if ("@graph" in item):
                for subitem in item["@graph"]:
                    retval.append(subitem)
            else:
                retval.append(item)
        return retval
    elif ("@graph" in js):
        return js["@graph"]
    else:
        return [js]
    

def add_embeddings_to_db(filename, num_to_process=1000000, site="imdb", first_drop=False):
    create_db(EMBEDDING_SIZE, first_drop)
    vectors = []
    num_done = 0
    if not os.path.exists(filename):
        print(f"Warning: File {filename} does not exist")
        return
    with open(filename) as f:
        for line in f:
            try:
                url, json_data, embedding_str = line.strip().split('\t')
                embedding_str = embedding_str.replace("[", "").replace("]", "") 
                embedding = [float(x) for x in embedding_str.split(',')]
                js = json.loads(json_data)
                js = normalize_list(js)
                found_items = False
            except Exception as e:
                print(f"Error processing line: {line}")
                print(f"Error: {e}")
                continue
           
            for i, item in enumerate(js):
                if not includeItem(item):                    
                    continue
                found_items = True
                item_url = url if i == 0 else f"{url}#{i}"
                name = getName(item)
                if (name == ""):
                    print(f"\n\n\nWarning: No name found for {item}")
                vectors.append({
                    "id": int64_hash(item_url),
                    "vector": embedding,
                    "text": item,
                    "url": item_url,
                    "name": name,
                    "site": site
                })
                continue
            if (len(vectors) > 1000):
                res = client.insert(
                    collection_name="prod_collection",
                    data=vectors
                )
       #         print("Added %d items to db from %s" % (len(vectors), filename))
                vectors = []
            if (found_items):
                num_done += 1
            if (num_done > num_to_process):
                break

    res = client.insert(
        collection_name="prod_collection",
        data=vectors
    )
    print("Added %i items to db from %s" % (num_done, filename))

#create_db()

if (EMBEDDING_SIZE == "small"):
    embeddings_path = EMBEDDINGS_PATH_SMALL
    client = MilvusClient("./milvus_small.db")
else:
    embeddings_path = EMBEDDINGS_PATH_LARGE
    client = MilvusClient("./milvus_large.db")


dbs = ["seriouseats",
    "woksoflife",
    "imdb", 
    "npr podcasts", 
    "neurips", 
    "backcountry", 
    "zillow", 
    "tripadvisor", 
    "seriouseats",
    "spruce",
       "cheftariq",
       "hebbarskitchen",
       "latam_recipes"
]

def create_all_dbs(embedding_size):
    if (embedding_size == "small"):
        size = 1536
    else:
        size = 3072
    if (client.has_collection("prod_collection")):
        client.drop_collection("prod_collection")
    if (not client.has_collection("prod_collection")):
        client.create_collection(
            collection_name="prod_collection",
            dimension=size
        )
    for db in dbs:
        filename = (embeddings_path + db + ".txt").replace(" ", "_")
        print(filename)
        add_embeddings_to_db(filename, 300000, db)

#search_db("alien movies")
#search_db("show me a science fiction movie that does not have aliens")

create_all_dbs("small")

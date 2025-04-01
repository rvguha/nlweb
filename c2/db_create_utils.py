
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

def shouldIncludeItem(js):
    if "@type" in js:
        item_type = js["@type"]
        if isinstance(item_type, list):
            if any(t in includeTypes for t in item_type):
                return True
        if item_type in includeTypes:
            return True
    elif "@graph" in js:
        for item in js["@graph"]:
            if shouldIncludeItem(item):
                return True

    return False

def getCSVItemName(js):
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

def normalizeCSVItemlist(js):
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
    
def documentsFromCSVLine(line, site):
    try:
        url, json_data, embedding_str = line.strip().split('\t')
        embedding_str = embedding_str.replace("[", "").replace("]", "") 
        embedding = [float(x) for x in embedding_str.split(',')]
        js = json.loads(json_data)
        js = normalizeCSVItemlist(js)
        found_items = False
    except Exception as e:
      #  print(f"Error processing line: {line}")
        print(f"Error: {e}")
        return []
    documents = []
    for i, item in enumerate(js):
        if not shouldIncludeItem(item):                    
            continue
        found_items = True
        item_url = url if i == 0 else f"{url}#{i}"
        name = getCSVItemName(item)
        if (name == ""):
            print(f"\n\n\nWarning: No name found for {item}")
        documents.append({
            "id": str(int64_hash(item_url)),
            "embedding": embedding,
            "schema_json": json.dumps(item),
            "url": item_url,
            "name": name,
            "site": site
        })
    return documents

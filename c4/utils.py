
recipe_sites = ['seriouseats', 'hebbarskitchen', 'latam_recipes',
                'woksoflife', 'cheftariq',  'spruce', 'nytimes']

all_sites = recipe_sites + ["imdb", "npr podcasts", "neurips", "backcountry", "tripadvisor"]

def siteToItemType(site):
    # For any single site's deployment, this can stay in code. But for the
    # multi-tenant, it should move to the database
    namespace = "http://nlweb.ai/base"
    et = "Item"
    if site == "imdb":
        et = "Movie"
    elif site in recipe_sites:
        et = "Recipe"
    elif site == "npr podcasts":
        et = "Thing"
    elif site == "neurips":
        et = "Paper"
    elif site == "backcountry":
        et = "Outdoor Gear"
    elif site == "tripadvisor":
        et = "Restaurant"
    elif site == "zillow":
        et = "RealEstate"
    else:
        et = "Items"
    return f"{{{namespace}}}{et}"
    

def itemTypeToSite(item_type):
    # this is used to route queries that this site cannot answer,
    # but some other site can answer. Needs to be generalized.
    sites = []
    for site in all_sites:
        if siteToItemType(site) == item_type:
            sites.append(site)
    return sites
    

def visibleUrlLink(url):
    from urllib.parse import urlparse

def visibleUrl(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc.replace('www.', '')


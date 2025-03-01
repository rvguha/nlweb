
from baseHandler import BaseNLWebHandler
from recipe import RecipeHandler
from context_sensitive import ContextSensitiveHandler
from loc_sensitive import LocationSensitiveHandler
from redirect import ItemTypeSensitiveRedirectHandler
from graph import GraphStructureHandler
from nlws import NLWSHandler

recipe_sites = ["seriouseats", "hebbarskitchen", "latam_recipes",
                  'woksoflife', 'cheftariq',  'spruce']

all_sites = recipe_sites + ["imdb", "npr podcasts", "neurips", "backcountry", "tripadvisor"]

def siteToItemType(site):
    if site == "imdb":
        return "Movie"
    elif site in recipe_sites:
        return "Recipe"
    elif site == "npr podcasts":
        return "Thing"
    elif site == "neurips":
        return "Paper"
    elif site == "backcountry":
        return "Outdoor Gear"
    elif site == "tripadvisor":
        return "Restaurant"
    else:
        return "Items"
    
def siteToClass(site):
    item_type = siteToItemType(site)
    if site == "imdb":
        return GraphStructureHandler
    elif site == "bc_product":
        return ContextSensitiveHandler
    elif site == "zillow":
        return LocationSensitiveHandler
    elif site == "latam_recipes":
        return ItemTypeSensitiveRedirectHandler
    elif item_type == "Recipe":
        return RecipeHandler
    elif site == "nlws":
        return NLWSHandler
    else:
        return BaseNLWebHandler
    
def itemTypeToSite(item_type):
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

async def execute_task_set (task_set):
    tasks = []
    for task in task_set:
        prompt = task[0]
        model = task[1]
        response_format = task[2]
        tasks.append(asyncio.create_task(ask_llm(prompt, model, response_format)))
    results =  await asyncio.gather(*tasks)
    return results
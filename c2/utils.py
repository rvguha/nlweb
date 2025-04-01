
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
    if site == "imdb" or "imdb" in site:
        return "Movie"
    elif site in recipe_sites:
        return "Recipe"
    elif isinstance(site, list) and site[0] in recipe_sites:
        return "Recipe"
    elif site == "npr podcasts":
        return "Thing"
    elif site == "neurips" or "neurips" in site:
        return "Paper"
    elif site == "backcountry" or "backcountry" in site:
        return "Outdoor Gear"
    elif site == "tripadvisor" or "tripadvisor" in site:
        return "Restaurant"
    else:
        return "Items"
    
def requestToHandlerClass(request):
   
    site = request.query_params.get('site', ['imdb'])
    context_url = request.query_params.get('context_url', '')
    item_type = siteToItemType(site)
    print(f"site: {site}, item_type: {item_type}")
    if "imdb" in site:
        return GraphStructureHandler
    elif context_url != '':
        return ContextSensitiveHandler
    elif "zillow" in site:
        return LocationSensitiveHandler
    elif "latam_recipes" in site:
        print("latam_recipes")
        return ItemTypeSensitiveRedirectHandler
    elif item_type == "Recipe":
        return RecipeHandler
    elif "nlws" in site:
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
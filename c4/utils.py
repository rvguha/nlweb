
import xml.etree.ElementTree as ET

recipe_sites = ["seriouseats", "hebbarskitchen", "latam_recipes",
                  'woksoflife', 'cheftariq',  'spruce']

all_sites = recipe_sites + ["imdb", "npr podcasts", "neurips", "backcountry", "tripadvisor"]

def siteToItemType(site):
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
    else:
        et = "Items"
    return f"{{{namespace}}}{et}"
    
def requestToHandlerClass(request):
   
    site = request.query_params.get('site', ['imdb'])
    context_url = request.query_params.get('context_url', '')
    item_type = siteToItemType(site)

    if site == "imdb":
        return GraphStructureHandler
    elif context_url != '':
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
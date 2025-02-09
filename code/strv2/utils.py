
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
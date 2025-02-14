import json
import asyncio
from recipe import RecipeHandler   
import mllm
import utils

class LatamHandler(RecipeHandler):

    MEMORY_PROMPT = ["""The user is interacting with the site {self.site}. Analyze the following statement from the user. 
     Is the user asking you to remember, something about their dietary restriction? For example, are they
     saying that they are vegetarian, or have some allergy? If so, what is the restriction?
     The user's statement is: {self.query}.""", 
     {"is_dietary_restriction" : "True or False", "dietary_restriction" : "The dietary restriction, if any"}]


    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
       # self.firstQueryResponse()

    async def analyzeQueryForItemType(self):
        prompt_str, ans_struc = self.DETERMINE_ITEM_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.item_type = response["item_type"]

    async def analyzeQuery(self):
        print("latam analyze query")
        task_set = [asyncio.create_task(self.isDietaryRestriction()), 
                    asyncio.create_task(self.analyzeQueryForItemType()),
                    asyncio.create_task(self.decontextualizeQuery())]
        await asyncio.gather(*task_set)
        self.http_handler.logger.info(f"item_type in latam: {self.item_type}")
        if (self.item_type != utils.siteToItemType(self.site)):
             sites = utils.itemTypeToSite(self.item_type)
             message = {"message_type": "remember", "item_to_remember": 
                       self.query, "message": "Asking " + " ".join(sites)}
             await self.http_handler.write_stream(message)
             self.http_handler.logger.info(f"Setting site to {sites}")
             self.site = sites 


    



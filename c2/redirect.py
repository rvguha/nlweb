import asyncio
from baseHandler import BaseNLWebHandler
import mllm
import utils

class ItemTypeSensitiveRedirectHandler(BaseNLWebHandler):

    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)

    async def analyzeQueryForItemType(self):
        prompt_str, ans_struc = self.DETERMINE_ITEM_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.item_type = response["item_type"]

    async def analyzeQuery(self):
        print("redirect analyze query")
        task_set = [asyncio.create_task(self.analyzeQueryForItemType()),
                    asyncio.create_task(self.retrieveItemsProactve()),
                    asyncio.create_task(self.decontextualizeQuery())]
        await asyncio.gather(*task_set)
        if (self.item_type != utils.siteToItemType(self.site)):
             sites = utils.itemTypeToSite(self.item_type)
             print(f"redirect sites: {sites}")
             message = {"message_type": "remember", "item_to_remember": 
                       self.query, "message": "Asking " + " ".join(sites)}
             await self.http_handler.write_stream(message)
             self.site = sites 


    



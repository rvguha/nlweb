import asyncio
from baseHandler import BaseNLWebHandler
import mllm
import utils
import retriever
from trim import trim_json

FIND_ITEM_THRESHOLD = 75

class ZillowHandler(BaseNLWebHandler):

    LOCATION_KNOWN_PROMPT = ["""The user is interacting with the site {self.site}. Analyze the following query from the user. 
     Does the user's query contain a location?
     The user's statement is: {self.query}.""", 
     {"location_known" : "True or False", "location" : "The location, if any"}]
    
    
    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
       # self.firstQueryResponse()

    async def isLocationKnown(self):
        prompt_str, ans_struc = self.LOCATION_KNOWN_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.location_known = response["location_known"]
        self.location = response["location"]

    async def analyzeQuery(self):
        print("imdb2 analyze query")
        task_set = [asyncio.create_task(self.isLocationKnown()), 
                    asyncio.create_task(self.decontextualizeQuery())]
        await asyncio.gather(*task_set)
        self.http_handler.logger.info(f"location_known in zillow: {self.location_known}")
       
    async def getRankedAnswers(self):
        await self.analyzeQuery()
        if (self.location_known == "True"):
            await super().getRankedAnswers()
        else:
            message = {"message_type": "remember",  "message": "Which city / area are you interested in?"}
            await self.http_handler.write_stream(message)
            return
   


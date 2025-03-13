import asyncio
from baseHandler import BaseNLWebHandler
import mllm
import utils
import retriever
from trim import trim_json

FIND_ITEM_THRESHOLD = 75

class GraphStructureHandler(BaseNLWebHandler):

    QUERY_TYPE_PROMPT = ["""The user is interacting with the site {self.site}. Analyze the following query from the user. 
     Is the user asking for a list {self.item_type} that match a certain description or are they asking for the details of a particular {self.item_type}?
      If the user for the details of a particular {self.item_type}, what is the title of the {self.item_type} and what details are they asking for?
     The user's statement is: {self.query}.""", 
     {"item_details_query" : "True or False", "item_title" : "The title of the {self.item_type}, if any", 
      "details_being_asked": "what details the user is asking for"}]
    
    FIND_ITEM_PROMPT = ["""The user is interacting with the site {self.site}. 
    The user is asking for a {self.item_type} {self.item_title}. Assign a score between 0 and 100 for whether
                        the {self.item_type} with the following description is the one the user is looking for.
    The description of the {self.item_type} is: {description}""", 
    {"score" : "integer between 0 and 100", "explanation" : "explanation of the relevance of the {self.item_type} to the user's question"}]

    ITEM_DETAILS_PROMPT = ["""The user is interacting with the site {self.site}. 
                            The user is asking a question about the {self.item_type} described below. 
                            Answer the user's question from the 
                            details of the {self.item_type}, mentioning the {self.item_type} title. 
                            Be concise and include a link to the page on {self.site} where this object is described.
                            The details of the {self.item_type} are: {schema_object}
                            The user's question is: {self.query}.""", 
                            {"item_details" : "The details of the {self.item_type}"}]


    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
       # self.firstQueryResponse()

    async def isItemDetailsQuery(self):
        prompt_str, ans_struc = self.QUERY_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.item_details_query = response["item_details_query"]
        self.item_title = response["item_title"]
        self.details_being_asked = response["details_being_asked"]

    async def analyzeQueryForItemType(self):
        prompt_str, ans_struc = self.DETERMINE_ITEM_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
      #  print(f"response: {response}")
        self.item_type = response["item_type"]

    async def analyzeQuery(self):
        if (self.query_analysis_done):
            return
        print("graph analyze query")
        task_set = [asyncio.create_task(self.isItemDetailsQuery()), 
                    asyncio.create_task(self.analyzeQueryForItemType()),
                    asyncio.create_task(self.decontextualizeQuery()),
                    asyncio.create_task(self.retrieveItemsProactve())]
        self.query_analysis_done = True
        await asyncio.gather(*task_set)
       
    async def getRankedAnswers(self):
        await self.analyzeQuery()
        if (self.item_details_query == "False"):
            await super().getRankedAnswers()
        else:
            item_name = self.item_title
            top_embeddings = retriever.search_db(item_name, self.site)
            tasks = []
            for url, json_str, name, site in top_embeddings:
                tasks.append(asyncio.create_task(self.findItem(url, json_str, name, site)))
            await asyncio.gather(*tasks)
            if (self.item_found):
                return
            else:
                message = {"message_type": "remember",  "message": "Could not find any movies that match your query"}
                await self.http_handler.write_stream(message)

    async def findItem (self, url, json_str, name, site):
        prompt_str, ans_struc = self.FIND_ITEM_PROMPT
        description = trim_json(json_str)
        prompt = prompt_str.format(self=self, description=description)
        ranking = await mllm.get_structured_completion_async(prompt, ans_struc, self.model)
        if (ranking["score"] > FIND_ITEM_THRESHOLD):
     #       print(f"Ranking: {ranking}")
            ansr = {
                'url': url,
                'site': site,
                'name': name,
                'ranking': ranking,
                'schema_object': json_str,
                'sent': False
            }
            self.item_found = True
            await self.returnItemDetails(ansr)

    async def returnItemDetails(self, item):   
        prompt_str, ans_struc = self.ITEM_DETAILS_PROMPT
        prompt = prompt_str.format(self=self, schema_object=item["schema_object"])
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
      
        message = {"message_type": "item_details", 
                   "message": response["item_details"]}
        await self.http_handler.write_stream(message)




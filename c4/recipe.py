import json
import asyncio
from baseHandler import BaseNLWebHandler
import mllm

class RecipeHandler(BaseNLWebHandler):

    MEMORY_PROMPT = ["""The user is querying the site {self.site}. Analyze the following statement from the user. 
     Is the user asking you to remember, something about their dietary restriction? If so, what is the restriction? 
     The user should be explicitly asking you to remember something about their dietary restriction, 
                     not just expressing a requirement for the current query.
     The user's query is: {self.query}.""", 
     {"is_dietary_restriction" : "True or False", "dietary_restriction" : "The dietary restriction, if any"}]


    RANKING_PROMPT = ["""Assign a score between 0 and 100 to the following recipe
    based on how relevant it is to the user's question. 
    Provide a short description of the recipe that is relevant to the user's question, without mentioning the user's question.
    The description should highlight aspects of the recipe the user is looking for, especially nutritional requirements, if any.
                       If the recipe is not for the dish that the user is looking for, specify, in the description, how this recipe might be useful in preparing what the user is trying to cook. 
The user's question is: {self.decontextualized_query}.
The item is: {description}.""", 
{"score" : "integer between 0 and 100", 
 "description" : "short description of the recipe", 
 "explanation" : "explanation of the relevance of the recipe to the user's question"}
]

    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
       # self.firstQueryResponse()

    async def analyzeQuery(self):
        print("recipe analyze query")
        task_set = [asyncio.create_task(self.isDietaryRestriction()), 
                    asyncio.create_task(self.decontextualizeQuery()),
                    asyncio.create_task(self.retrieveItemsProactve())]
        await asyncio.gather(*task_set)

    async def isDietaryRestriction(self):
        prompt_str, ans_struc = self.MEMORY_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.is_dietary_restriction = response["is_dietary_restriction"]
        self.dietary_restriction = response["dietary_restriction"]
        if (self.is_dietary_restriction == "True"):
            message = {"message_type": "remember", "item_to_remember": self.dietary_restriction, "message": "I'll remember that"}
            await self.http_handler.write_stream(message)
       



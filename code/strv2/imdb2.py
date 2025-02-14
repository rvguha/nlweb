import asyncio
from baseHandler import BaseNLWebHandler
import mllm
import utils

class Imdb2Handler(BaseNLWebHandler):

    QUERY_TYPE_PROMPT = ["""The user is interacting with the site {self.site}. Analyze the following query from the user. 
     Is the user asking for a list movies that match a certain description or are they asking for the details of a particular movie?
      If the user for the details of a particular movie, what is the title of the movie and what details are they asking for?
     The user's statement is: {self.query}.""", 
     {"movie_details_query" : "True or False", "movie_title" : "The title of the movie, if any", 
      "details": "what details the user is asking for"}]
    
    MOVIE_DETAILS_PROMPT = ["""The user is interacting with the site {self.site}. 
                            The user is asking for the details of the movie described below. Answer the user's question from the 
                            details of the movie.
                            The details of the movie are: {schema_object}
                            The user's statement is: {self.query}.""", 
                            {"movie_details" : "The details of the movie"}]


    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
       # self.firstQueryResponse()

    async def isMovieDetailsQuery(self):
        prompt_str, ans_struc = self.QUERY_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.movie_details_query = response["movie_details_query"]
        self.movie_title = response["movie_title"]

    async def analyzeQueryForItemType(self):
        prompt_str, ans_struc = self.DETERMINE_ITEM_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.item_type = response["item_type"]

    async def analyzeQuery(self):
        print("imdb2 analyze query")
        task_set = [asyncio.create_task(self.isMovieDetailsQuery()), 
                    asyncio.create_task(self.analyzeQueryForItemType()),
                    asyncio.create_task(self.decontextualizeQuery())]
        await asyncio.gather(*task_set)
        self.http_handler.logger.info(f"item_type in imdb2: {self.item_type}")
        if (self.movie_details_query):
            self.streaming = False
        
    
    async def getRankedAnswers(self):
        await self.analyzeQuery()
        await super().getRankedAnswers()
        if (self.movie_details_query):
           await self.getMovieDetails()

    async def getMovieDetails(self):
        items = []
        for item in self.rankedAnswers:
         #   print(f"item: {item['name']}, score: {item['ranking']['score']}")
            if (item["ranking"]["score"] > 60):
                items.append(item)
        if (len(items) == 0):
            message = {"message_type": "remember",  "message": "Could not find any movies that match your query"}
            await self.http_handler.write_stream(message)
        else :
            print(f"returning details for {len(items)} movies")
            tasks = []
            for item in items:
                tasks.append(self.returnMovieDetails(item))
            await asyncio.gather(*tasks)
       

    async def returnMovieDetails(self, item):   
        prompt_str, ans_struc = self.MOVIE_DETAILS_PROMPT
        prompt = prompt_str.format(self=self, schema_object=item["schema_object"])
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        message = {"message_type": "remember", "item_to_remember": item, 
                   "message": response["movie_details"]}
        await self.http_handler.write_stream(message)




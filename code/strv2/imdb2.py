import asyncio
from baseHandler import BaseNLWebHandler
import mllm
import utils
import retriever
from trim import trim_json

FIND_ITEM_THRESHOLD = 75

class Imdb2Handler(BaseNLWebHandler):

    QUERY_TYPE_PROMPT = ["""The user is interacting with the site {self.site}. Analyze the following query from the user. 
     Is the user asking for a list movies that match a certain description or are they asking for the details of a particular movie?
      If the user for the details of a particular movie, what is the title of the movie and what details are they asking for?
     The user's statement is: {self.query}.""", 
     {"movie_details_query" : "True or False", "movie_title" : "The title of the movie, if any", 
      "details_being_asked": "what details the user is asking for"}]
    
    FIND_ITEM_PROMPT = ["""The user is interacting with the site {self.site}. 
    The user is asking for a movie {self.movie_title}. Assign a score between 0 and 100 for whether
                        the movie with the following description is the one the user is looking for.
    The description of the movie is: {description}""", 
    {"score" : "integer between 0 and 100", "explanation" : "explanation of the relevance of the movie to the user's question"}]

    MOVIE_DETAILS_PROMPT = ["""The user is interacting with the site {self.site}. 
                            The user is asking a question about the movie described below. 
                            Answer the user's question from the 
                            details of the movie.
                            The details of the movie are: {schema_object}
                            The user's question is: {self.query}.""", 
                            {"movie_details" : "The details of the movie"}]


    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
       # self.firstQueryResponse()

    async def isMovieDetailsQuery(self):
        prompt_str, ans_struc = self.QUERY_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.movie_details_query = response["movie_details_query"]
        self.movie_title = response["movie_title"]
        self.details_being_asked = response["details_being_asked"]

    async def analyzeQueryForItemType(self):
        prompt_str, ans_struc = self.DETERMINE_ITEM_TYPE_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
      #  print(f"response: {response}")
        self.item_type = response["item_type"]

    async def analyzeQuery(self):
        print("imdb2 analyze query")
        task_set = [asyncio.create_task(self.isMovieDetailsQuery()), 
                    asyncio.create_task(self.analyzeQueryForItemType()),
                    asyncio.create_task(self.decontextualizeQuery())]
        await asyncio.gather(*task_set)
        self.http_handler.logger.info(f"item_type in imdb2: {self.item_type}")
       
    async def getRankedAnswers(self):
        await self.analyzeQuery()
        if (self.movie_details_query == "False"):
            await super().getRankedAnswers()
        else:
            item_name = self.movie_title
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
            print(f"Ranking: {ranking}")
            ansr = {
                'url': url,
                'site': site,
                'name': name,
                'ranking': ranking,
                'schema_object': json_str,
                'sent': False
            }
            self.item_found = True
            await self.returnMovieDetails(ansr)

    async def returnMovieDetails(self, item):   
        prompt_str, ans_struc = self.MOVIE_DETAILS_PROMPT
        prompt = prompt_str.format(self=self, schema_object=item["schema_object"])
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        message = {"message_type": "item_details", 
                   "message": response["movie_details"]}
        await self.http_handler.write_stream(message)




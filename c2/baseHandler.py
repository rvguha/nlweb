import mllm
import azure_completion
import retriever
import asyncio
import json
import utils
from trim import trim_json
import time

NUM_RESULTS_TO_SEND = 10
EARLY_SEND_THRESHOLD = 55

class BaseNLWebHandler :
    # [Existing prompts remain unchanged]
    DETERMINE_ITEM_TYPE_PROMPT = [
        """What is the kind of item the query is seeking with this query: {self.query}? 
        Pick one of [Recipe, Restaurant, Movie, Paper, Outdoor Gear, Podcast]""", 
        {"item_type" : ""}]
    
    DECONTEXTUALIZE_QUERY_PROMPT = ["""This site has information about {self.item_type}
     Does answering this query require access to earlier queries? 
    If so, rewrite the query to decontextualize it so that it can be answered 
    without reference to earlier queries. If not, don't change the query.
  . The user's query is: {self.query}. Previous queries were: {self.prev_queries}.""",
                                    {"requires_decontextualization" : "True or False", 
                                     "decontextualized_query" : "The rewritten query"}]
    
    
    OLD_RANKING_PROMPT = ["""Assign a score between 0 and 100 to the following {self.item_type}
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement.
Provide a short description of the item that is relevant to the user's question, without mentioning the user's question.
Provide an explanation of the relevance of the item to the user's question, without mentioning the user's question or the score or explicitly mentioning the term relevance.
If the score is below 75, in the description, include the reason why it is still relevant.
The user's question is: {self.decontextualized_query}.
The item is: {description}.""" , {"score" : "integer between 0 and 100", 
 "description" : "short description of the item", 
 "explanation" : "explanation of the relevance of the item to the user's question"}]
    
    RANKING_PROMPT = ["""Assign a score between 0 and 100 to the following {self.item_type}
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement.
If the score is over 50, provide a short description, of less than 50 words, of the item showing its relevant to the user's question, without mentioning the user's question.

The user's question is: {self.decontextualized_query}.
The item is: {description}.""" , {"score" : "integer between 0 and 100", 
 "description" : "short description of the item"}]

    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        self.site = site
        self.query = query
        self.prev_queries = prev_queries
        self.model = model
        self.http_handler = http_handler
        self.query_id = query_id
        self.simpleItemType()
        self.rankedAnswers = []
        self.num_results_sent = 0
        self.sites_in_embeddings_sent = False
        self.streaming = True
        self.is_connection_alive = True  # Flag to track connection state
        self.query_analysis_done = False
        self.requires_decontextualization = False
        self.retrieved_items = []


    def get_formatted_string(self):
        # This will replace all {self.xxx} with the actual instance variable values
        return self.format_string.format(self=self)
    
    def firstQueryResponse(self):
        return

    def simpleItemType(self):
        self.item_type = utils.siteToItemType(self.site)

    async def analyzeQuery(self):
       if (self.query_analysis_done):
           return
       tasks = [asyncio.create_task(self.decontextualizeQuery()),
                asyncio.create_task(self.retrieveItemsProactve())]
       await asyncio.gather(*tasks)
       self.query_analysis_done = True

    async def retrieveItemsProactve(self):
        self.retrieved_items = await retriever.search_db(self.query, self.site)
          
    async def decontextualizeQuery(self):
        if (len(self.prev_queries) < 5):
            print("not decontextualizing")
            self.decontextualized_query = self.query
            return
        prompt_str, ans_struc = self.DECONTEXTUALIZE_QUERY_PROMPT
        prompt = prompt_str.format(self=self)
        #response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        response = await azure_completion.get_completion(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        self.requires_decontextualization = response["requires_decontextualization"]
        self.decontextualized_query = response["decontextualized_query"]
        if (self.decontextualized_query != self.query):
            message = {"message_type": "decontextualized_query", "query": self.decontextualized_query}
            try:
                await self.http_handler.write_stream(message)
                print(f"Decontextualized query: {self.decontextualized_query}")
            except (BrokenPipeError, ConnectionResetError):
                print("Client disconnected during decontextualization")
                self.is_connection_alive = False


    async def rankItem(self, url, json_str, name, site):
        if not self.is_connection_alive:
            # Skip processing if connection is already known to be lost
            return

        try:
            prompt_str, ans_struc = self.RANKING_PROMPT
            schema_object = json.loads(json_str)
            description = trim_json(schema_object)
            prompt = prompt_str.format(self=self, description=description)  
            start_time = time.time()
            #ranking = await mllm.get_structured_completion_async(prompt, ans_struc, self.model)
            ranking = await azure_completion.get_completion(prompt, ans_struc, self.model)
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
           # print(f"Ranking completion took {processing_time:.2f} seconds")
            ansr = {
                'url': url,
                'site': site,
                'name': name,
                'ranking': ranking,
                'schema_object': schema_object,
                'sent': False,
                'time': processing_time
            }
            if (ranking["score"] > EARLY_SEND_THRESHOLD and self.streaming and self.is_connection_alive):
                try:
                    await self.sendAnswers([ansr])
                except (BrokenPipeError, ConnectionResetError):
                    print(f"Client disconnected while sending early answer for {name}")
                    self.is_connection_alive = False
                    return
            
            self.rankedAnswers.append(ansr)
        except Exception as e:
            print(f"Error in rankItem for {name}: {str(e)}")
            # Continue with other items even if one fails


    def shouldSend(self, result):
        if (self.num_results_sent < NUM_RESULTS_TO_SEND - 5):
            return True
        for r in self.rankedAnswers:
            if r["sent"] == True and r["ranking"]["score"] < result["ranking"]["score"]:
                return True
        return False
    
    async def sendAnswers(self, answers, force=False):
        if not self.is_connection_alive:
            return
            
        json_results = []
        for result in answers:
            if self.shouldSend(result) or force:
                json_results.append({
                    "url": result["url"],
                    "name": result["name"],
                    "site": result["site"],
                    "siteUrl": result["site"],
                    "score": result["ranking"]["score"],
                    "time": result["time"],
                    "description": result["ranking"]["description"],
                    "explanation": "", #result["ranking"]["explanation"],
                    "schema_object": result["schema_object"],
                })
                if (self.streaming):
                    result["sent"] = True
            
        if (self.streaming and json_results):  # Only attempt to send if there are results
            try:
                to_send = {"message_type": "result_batch", "results": json_results, "query_id": self.query_id}
                await self.http_handler.write_stream(to_send)
                self.num_results_sent += len(json_results)
            except (BrokenPipeError, ConnectionResetError) as e:
                print(f"Client disconnected while sending answers: {str(e)}")
                self.is_connection_alive = False
                # Don't re-raise the exception - just record that connection is lost
            except Exception as e:
                print(f"Error sending answers: {str(e)}")
                self.is_connection_alive = False
        

    def prettyPrintSite(self, site):
        ans = site.replace("_", " ")
        words = ans.split()
        return ' '.join(word.capitalize() for word in words)

    async def sendMessageOnSitesBeingAsked(self, top_embeddings):
        if not self.is_connection_alive:
            return
            
        if ((self.site == "all" or self.site == "nlws") and not self.sites_in_embeddings_sent):
            sites_in_embeddings = {}
            for url, json_str, name, site in top_embeddings:
                sites_in_embeddings[site] = sites_in_embeddings.get(site, 0) + 1
            top_sites = sorted(sites_in_embeddings.items(), key=lambda x: x[1], reverse=True)[:3]
            top_sites_str = ", ".join([self.prettyPrintSite(x[0]) for x in top_sites])
            message = {"message_type": "remember", "item_to_remember": 
                      self.query, "message": "Asking " + top_sites_str}
            try:
                await self.http_handler.write_stream(message)
                self.sites_in_embeddings_sent = True
            except (BrokenPipeError, ConnectionResetError):
                print("Client disconnected when sending sites message")
                self.is_connection_alive = False
    
    async def getRankedAnswers(self):
        print("Getting ranked answers xxx")
        try:
            await self.analyzeQuery()
            if not self.is_connection_alive:
                print("Connection lost during analysis, skipping further processing")
                return
            
            if (self.requires_decontextualization == "True"):
                top_embeddings = await retriever.search_db(self.decontextualized_query, self.site)
            else:
                top_embeddings = self.retrieved_items

            if (self.site == "all" or self.site == "nlws"):
                await self.sendMessageOnSitesBeingAsked(top_embeddings)

            tasks = []
           
            for url, json_str, name, site in top_embeddings:
                if self.is_connection_alive:  # Only add new tasks if connection is still alive
                    tasks.append(asyncio.create_task(self.rankItem(url, json_str, name, site)))
            
            # Wait for all rankings to complete
            if tasks:  # Only gather if there are tasks
                # Use gather with return_exceptions=True to handle exceptions in individual tasks
                await asyncio.gather(*tasks, return_exceptions=True)
                
            if not self.is_connection_alive:
                print("Connection lost during ranking, skipping sending results")
                return
                
            results = [r for r in self.rankedAnswers if r['sent'] == False]
            if (self.num_results_sent > NUM_RESULTS_TO_SEND):
                print("returning without looking at remaining results")
                return
       
            # Sort by score in descending order
            sorted_results = sorted(results, key=lambda x: x['ranking']["score"], reverse=True)
            good_results = [x for x in sorted_results if x['ranking']["score"] > 51]
            medium_results = [x for x in sorted_results if x['ranking']["score"] > 35 and x['ranking']["score"] < 51]
            print(f"num_results_sent: {self.num_results_sent}, len(results): {len(good_results)}")

            if (len(good_results) + self.num_results_sent >= NUM_RESULTS_TO_SEND):
                tosend = good_results[:NUM_RESULTS_TO_SEND - self.num_results_sent + 1]
                print(f"sending {len(tosend)} results")
                try:
                    await self.sendAnswers(tosend, force=True)
                except (BrokenPipeError, ConnectionResetError):
                    print("Client disconnected during final answer sending")
                    self.is_connection_alive = False
            else:
                try:
                    await self.sendAnswers(good_results, force=True)
                    self.num_results_sent = self.num_results_sent + len(good_results)
                except (BrokenPipeError, ConnectionResetError):
                    print("Client disconnected during final answer sending")
                    self.is_connection_alive = False
                    
        except Exception as e:
            print(f"Unexpected error in getRankedAnswers: {str(e)}")
            # Let the outer handler deal with this error
            raise
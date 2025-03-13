import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json

NUM_RESULTS_TO_SEND = 10
EARLY_SEND_THRESHOLD = 55

class BaseNLWebHandler :

    DETERMINE_ITEM_TYPE_PROMPT = [
        """What is the kind of item the query is seeking with this query: {self.query}? 
        Pick one of [Recipe, Restaurant, Movie, Paper, Outdoor Gear, Podcast]""", 
        {"item_type" : ""}]
    
    DECONTEXTUALIZE_QUERY_PROMPT = ["""This site has information about {self.item_type}
     Does answering this query require access to earlier queries? If so, rewrite the query to decontextualize it so that it can be answered without reference to earlier queries.
  . The user's query is: {self.query}. Previous queries were: {self.prev_queries}.""",
                                    {"decontextualized_query" : "The rewritten query"}]
    
    
    RANKING_PROMPT = ["""Assign a score between 0 and 100 to the following {self.item_type}
based on how relevant it is to the user's question. Use your knowledge from other sources, about the item, to make a judgement.
Provide a short description of the item that is relevant to the user's question, without mentioning the user's question.
Provide an explanation of the relevance of the item to the user's question, without mentioning the user's question or the score or explicitly mentioning the term relevance.
If the score is below 75, in the description, include the reason why it is still relevant.
The user's question is: {self.decontextualized_query}.
The item is: {description}.""" , {"score" : "integer between 0 and 100", 
 "description" : "short description of the item", 
 "explanation" : "explanation of the relevance of the item to the user's question"}]

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


    def get_formatted_string(self):
        # This will replace all {self.xxx} with the actual instance variable values
        return self.format_string.format(self=self)
    
   
    def simpleItemType(self):
        self.item_type = utils.siteToItemType(self.site)

    async def analyzeQuery(self):
       tasks = [asyncio.create_task(self.decontextualizeQuery())]
       await asyncio.gather(*tasks)

    async def decontextualizeQuery(self):
        if (len(self.prev_queries) < 5):
            print("not decontextualizing")
            self.decontextualized_query = self.query
            return
        prompt_str, ans_struc = self.DECONTEXTUALIZE_QUERY_PROMPT
        prompt = prompt_str.format(self=self)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        self.decontextualized_query = response["decontextualized_query"]
        if (self.decontextualized_query != self.query):
            message = {"message_type": "decontextualized_query", "query": self.decontextualized_query}
            await self.http_handler.write_stream(message)
            print(f"Decontextualized query: {self.decontextualized_query}")  


    async def rankItem (self, url, json_str, name, site):
        prompt_str, ans_struc = self.RANKING_PROMPT
        description = trim_json(json_str)
        prompt = prompt_str.format(self=self, description=description)
        ranking = await mllm.get_structured_completion_async(prompt, ans_struc, self.model)
        # print(f"Ranking: {ranking}")
        ansr = {
            'url': url,
            'site': site,
            'name': name,
            'ranking': ranking,
            'schema_object': json_str,
            'sent': False
        }
        if (ranking["score"] > EARLY_SEND_THRESHOLD and self.streaming):
            await self.sendAnswers([ansr])
        self.rankedAnswers.append(ansr)


    def shouldSend(self, result):
        if (self.num_results_sent < NUM_RESULTS_TO_SEND - 5):
            return True
        for r in self.rankedAnswers:
            if r["sent"] == True and r["ranking"]["score"] < result["ranking"]["score"]:
                return True
        return False
    
    async def sendAnswers(self, answers, force=False):
        json_results = []
        for result in answers:
            if self.shouldSend(result) or force:
                json_results.append({
                    "url": result["url"],
                    "name": result["name"],
                    "site": result["site"],
                    "siteUrl": result["site"],
                    "score": result["ranking"]["score"],
                    "description": result["ranking"]["description"],
                    "explanation": result["ranking"]["explanation"],
                    "schema_object": result["schema_object"],
                })
                if (self.streaming):
                    result["sent"] = True
            
        if (self.streaming):
            try:
                to_send = {"message_type": "result_batch", "results": json_results, "query_id": self.query_id}
                await self.http_handler.write_stream(to_send)
                self.num_results_sent += len(json_results)
            except (BrokenPipeError, ConnectionResetError):
                #   print("Client disconnected while sending answers")
                raise
        

    def prettyPrintSite(self, site):
        ans = site.replace("_", " ")
        words = ans.split()
        return ' '.join(word.capitalize() for word in words)

    async def sendMessageOnSitesBeingAsked(self, top_embeddings):
        if (self.site == "all" and not self.sites_in_embeddings_sent):
            sites_in_embeddings = {}
            for url, json_str, name, site in top_embeddings:
                sites_in_embeddings[site] = sites_in_embeddings.get(site, 0) + 1
            top_sites = sorted(sites_in_embeddings.items(), key=lambda x: x[1], reverse=True)[:4]
            top_sites_str = ", ".join([self.prettyPrintSite(x[0]) for x in top_sites])
            print(f"sites in embeddings: {top_sites}")
            message = {"message_type": "remember", "item_to_remember": 
                       self.query, "message": "Asking " + top_sites_str}
            await self.http_handler.write_stream(message)
        self.sites_in_embeddings_sent = True

    
    async def getRankedAnswers(self):
        await self.analyzeQuery()
        top_embeddings = retriever.search_db(self.decontextualized_query, self.site)

        if (self.site == "all"):
            await self.sendMessageOnSitesBeingAsked(top_embeddings)

        tasks = []
       
        for url, json_str, name, site in top_embeddings:
            tasks.append(asyncio.create_task(self.rankItem(url, json_str, name, site)))
        
        # Wait for all rankings to complete
        await asyncio.gather(*tasks)
        results = [r for r in self.rankedAnswers if r['sent'] == False]
        if (self.num_results_sent > NUM_RESULTS_TO_SEND):
            print("returning without looking at remaining results")
            return
   
        sorted_results = sorted(results, key=lambda x: x['ranking']["score"], reverse=True)
        good_results = [x for x in sorted_results if x['ranking']["score"] > 51]
        medium_results = [x for x in sorted_results if x['ranking']["score"] > 35 and x['ranking']["score"] < 51]
        print(f"num_results_sent: {self.num_results_sent}, len(results): {len(good_results)}")

        if (len(good_results) + self.num_results_sent >= NUM_RESULTS_TO_SEND):
            tosend = good_results[:NUM_RESULTS_TO_SEND - self.num_results_sent + 1]
            print(f"sending {len(tosend)} results")
            await self.sendAnswers(tosend, force=True)
        else:
            await self.sendAnswers(good_results, force=True)
            self.num_results_sent = self.num_results_sent + len(good_results)

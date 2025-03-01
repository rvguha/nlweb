import asyncio
from baseHandler import BaseNLWebHandler
import mllm
import utils
import retriever
from trim import trim_json, trim_json_hard

GATHER_ITEMS_THRESHOLD = 55

class NLWSHandler(BaseNLWebHandler):

    RANKING_PROMPT = ["""Assign a score between 0 and 100 to the following {self.item_type}
based on useful it might be to answering the user's question. 
The user's question is: {self.decontextualized_query}.
The item is: {description}.""" , {"score" : "integer between 0 and 100"}]
     

 
     
    SYNTHESIZE_PROMPT = ["""Given the following items, synthesize an answer to the user's question. 
                          You do not need to include all the items, but you should include the most relevant ones.
                          For each of the items included in the answer, provide the url of the item. Pick items from 
                          different sites, if possible.
                          The user's question is: {self.decontextualized_query}.
                          The items are: {self.items}.""" , 
                          {"answer" : "string", "urls" : "urls of the items included in the answer"}]
     
    def __init__(self, site, query, prev_queries=[], model="gpt-4o", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
        print("Got here")
        self.items = []
        # self.firstQueryResponse()

    async def analyzeQuery(self):
        print("graph analyze query")
        await self.decontextualizeQuery()
       
    async def getRankedAnswers(self):
        await self.analyzeQuery()
        top_embeddings = retriever.search_db(self.decontextualized_query, self.site)
        await self.sendMessageOnSitesBeingAsked(top_embeddings)
        tasks = []
        for url, json_str, name, site in top_embeddings:
            tasks.append(asyncio.create_task(self.gatherItems(url, json_str, name, site)))
        await asyncio.gather(*tasks)
        await self.synthesizeAnswer()

    async def gatherItems(self, url, json_str, name, site):
        prompt_str, ans_struc = self.RANKING_PROMPT
        description = trim_json_hard(json_str)
        prompt = prompt_str.format(self=self, description=description)
        ranking = await mllm.get_structured_completion_async(prompt, ans_struc, self.model)
        if (ranking["score"] > GATHER_ITEMS_THRESHOLD):
            self.items.append([url, json_str, name, site])

    async def synthesizeAnswer(self): 
        prompt_str, ans_struc = self.SYNTHESIZE_PROMPT
        prompt = prompt_str.format(self=self, items=self.items)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        print(f"response: {response}")
        json_results = []
        for url in response["urls"]:
            item = next((item for item in self.items if item[0] == url), None)
            if not item:
                continue
            (url, json_str, name, site) = item
            json_obj = json.loads(json_str) if isinstance(json_str, str) else json_str
            description = json_obj.get("description", "")
            json_results.append({
                    "url": url,
                    "name": name,
                    "description": description,
                    "site": site,
                    "schema_object": json_str,
                })
        message = {"message_type": "nlws", "answer": response["answer"], "items": json_results}
        await self.http_handler.write_stream(message)
   #     print(f"message: {message}")
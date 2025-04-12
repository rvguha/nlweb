import json
import asyncio
from baseHandler import BaseNLWebHandler
import mllm
from retriever import retrieve_item_with_url
from trim import trim_json, trim_json_hard
import azure_completion
import retriever
#http://localhost:8000/html/str_chat.html?query=similar+jackets+from+patagonia+with+hood&site=bc_product&context_url=https://www.backcountry.com/mountain-hardwear-firefall-2-jacket-womens

EARLY_SEND_THRESHOLD = 65

class ContextSensitiveHandler(BaseNLWebHandler):

    RANKING_PROMPT = ["""The user is interacting with the site {self.site} on the page for the product with the following description:
                      {description_context}.
    Assign a score between 0 and 100 to the product with the following description based on how relevant it is to the user's 
                      question, when asked in the context of the product page mentioned above.
    The user's question is: {self.decontextualized_query}.
    The description of the product is: {description}.""", 
    {"score" : "integer between 0 and 100", 
     "description" : "short description of the product",
     "explanation" : "explanation of the relevance of the product to the user's question"}]
    
    DECONTEXTUALIZE_QUERY_PROMPT = ["""The use is asking the following question: '{self.query}' in the context of the product with the following description: {description_context}. 
                                    Rewrite the query to decontextualize it so that it can be answered without reference to earlier queries or to the product description.""",
                                 
                                    {"decontextualized_query" : "The rewritten query"}]

    def __init__(self, site, query, prev_queries=[], model="gpt-4o-mini", http_handler=None, query_id=None, context_url=None):
        super().__init__(site, query, prev_queries, model, http_handler, query_id)
        self.context_url = context_url
       # self.firstQueryResponse()

    async def analyzeQuery(self):
        if (self.query_analysis_done):
            return
        await self.decontextualizeQuery()
        self.query_analysis_done = True

    async def getDescriptionContext(self):
        item = await retrieve_item_with_url(self.context_url)
        if item:
            url, schema_json, name, site = item
            self.description_context = trim_json(schema_json)
        else:
            self.description_context = ""

    async def decontextualizeQuery(self):
        await self.getDescriptionContext()
        prompt_str, ans_struc = self.DECONTEXTUALIZE_QUERY_PROMPT
        prompt = prompt_str.format(self=self, description_context=self.description_context)
        print(len(prompt))
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
      #  response = await azure_completion.get_completion(prompt, ans_struc, "gpt-4o")
        self.decontextualized_query = response["decontextualized_query"]
        self.requires_decontextualization = True
        if (self.decontextualized_query != self.query):
            message = {"message_type": "decontextualized_query", "query": self.decontextualized_query}
            await self.http_handler.write_stream(message)
            print(f"Decontextualized query: {self.decontextualized_query}")  
            self.retrieved_items = await retriever.search_db(self.decontextualized_query, self.site)
            print(f"Retrieved {len(self.retrieved_items)} items")




    async def rankItem (self, url, json_str, name, site):
        prompt_str, ans_struc = self.RANKING_PROMPT
        description = trim_json(json_str)
        description_context = self.description_context
        prompt = prompt_str.format(self=self, description=description, description_context=description_context)
      #  ranking = await mllm.get_structured_completion_async(prompt, ans_struc, self.model)
        ranking = await azure_completion.get_completion(prompt, ans_struc, self.model)
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
       



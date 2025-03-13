import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json
import decontextualize
import analyze_query
import memory   
import post_prepare
import ranking
import required_info
import traceback
import relevance_detection

NUM_RESULTS_TO_SEND = 10
EARLY_SEND_THRESHOLD = 55

class NLWebHandler :
    def __init__(self, http_handler): 
        self.http_handler = http_handler
        self.site = http_handler.get_param("site", str, "all")  
        self.query = http_handler.get_param("query", str, )
        self.prev_queries = http_handler.get_param("prev", list)
        self.model = http_handler.get_param("model", str, "gpt-4o-mini")
        self.query_id = http_handler.get_param("query_id", str, "")
        self.decontextualized_query = http_handler.get_param("decontextualized_query", str, "") 
        self.context_url = http_handler.get_param("context_url", str)
        self.context_description = ""
        self.retrieved_items = []
        self.query_done = False
        self.final_retrieved_items = []
        self.final_ranked_answers = []
        self.streaming = True
        self.is_connection_alive = True
        self.required_info = ""
        self.item_type = utils.siteToItemType(self.site)
        self.decontextualization_done = False

        print(f"NLWebHandler initialized with site: {self.site}, query: {self.query}, prev_queries: {self.prev_queries}, model: {self.model}, query_id: {self.query_id}, context_url: {self.context_url}")

    async def runQuery(self):
        await self.decontextualizeQuery()
        await self.prepare()
        await self.post_prepare_tasks()
        if (self.query_done):
            return
        await self.get_ranked_answers()
    
    async def decontextualizeQuery(self):
        if (self.context_url == '' and len(self.prev_queries) < 1):
            self.decontextualized_query = self.query
            self.decontextualization_done = True
            return
        elif (self.decontextualized_query != ''):
            self.decontextualization_done = True
            return
        else:
            decontextualizer = self.get_decontextualizer()
            await decontextualizer.do()
            self.decontextualization_done = True
            return
    
    async def prepare(self):
        try:
            tasks = []
            tasks.append(asyncio.create_task(self.get_relevance_detection().do()))
            tasks.append(asyncio.create_task(self.retrieve_items().do()))
            tasks.append(asyncio.create_task(self.get_analyze_query().do()))
            tasks.append(asyncio.create_task(self.detect_memory_items().do()))
            tasks.append(asyncio.create_task(self.ensure_required_info().do()))
            await asyncio.gather(*tasks)
            print(f"prepare tasks done")
        except Exception as e:
            print(f"Error in prepare: {e}")
            traceback.print_exc()

    def get_decontextualizer(self):
        decontextualizer = None
        print(f"decontextualize {self.context_url} {self.prev_queries}")
        if (len(self.prev_queries) < 1  and self.context_url == ''):
            decontextualizer = decontextualize.NoOpDecontextualizer(self)
        elif (self.context_url == '' and len(self.prev_queries) > 0):
            decontextualizer = decontextualize.PrevQueryDecontextualizer(self)
        elif (self.context_url != '' and len(self.prev_queries) == 0):
            decontextualizer = decontextualize.ContextUrlDecontextualizer(self)
        else:
            decontextualizer = decontextualize.FullDecontextualizer(self)
        print(f"decontextualizer: {decontextualizer}")
        return decontextualizer
        
    def detect_memory_items(self):
        return memory.Memory(self)
    
    def ensure_required_info(self):
        return required_info.RequiredInfo(self)
        
    def retrieve_items(self):
        return retriever.MilvusQueryRetriever(self)
    
    def get_analyze_query(self):
        return analyze_query.AnalyzeQuery(self)
    
    def get_relevance_detection(self):
        return relevance_detection.RelevanceDetection(self)
    
    async def post_prepare_tasks(self):
        await post_prepare.PostPrepare(self).do()
    
    async def get_ranked_answers(self):
        try:
            return await ranking.Ranking(self).do()
        except Exception as e:
            print(f"Error in get_ranked_answers: {e}")
            traceback.print_exc()


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
import fastTrack
from state import NLWebHandlerState

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
        self.query_is_irrelevant = False
        self.requires_decontextualization = False
        self.state = NLWebHandlerState(self)
        self.fastTrackRanker = None
        self.abort_fast_track = False
        print(f"NLWebHandler initialized with site: {self.site}, query: {self.query}, prev_queries: {self.prev_queries}, model: {self.model}, query_id: {self.query_id}, context_url: {self.context_url}")

    async def runQuery(self):
        try:
            await self.prepare()
            await self.post_prepare_tasks()
            if (self.query_done or not self.requires_decontextualization):
                return
            await self.get_ranked_answers()
        except Exception as e:
            print(f"Error in runQuery: {e}")
            traceback.print_exc()
    
    def decontextualizeQuery(self):
        if (self.context_url == '' and len(self.prev_queries) < 1):
            self.decontextualized_query = self.query
            return decontextualize.NoOpDecontextualizer(self)
        elif (self.decontextualized_query != ''):
            return decontextualize.NoOpDecontextualizer(self)
        elif (self.context_url == '' and len(self.prev_queries) > 0):
            return decontextualize.PrevQueryDecontextualizer(self)
        elif (self.context_url != '' and len(self.prev_queries) == 0):
            return decontextualize.ContextUrlDecontextualizer(self)
        else:
            return decontextualize.FullDecontextualizer(self)
            
    
    async def prepare(self):
        tasks = []
        self.state.analyze_query = NLWebHandlerState.IN_PROGRESS
        self.state.query_relevance = NLWebHandlerState.IN_PROGRESS
        self.state.required_info = NLWebHandlerState.IN_PROGRESS
        self.state.memory_items = NLWebHandlerState.IN_PROGRESS

        tasks.append(asyncio.create_task(self.decontextualizeQuery().do()))
        tasks.append(asyncio.create_task(fastTrack.FastTrack(self).do()))
        tasks.append(asyncio.create_task(self.get_relevance_detection().do()))
        tasks.append(asyncio.create_task(self.get_analyze_query().do()))
        tasks.append(asyncio.create_task(self.detect_memory_items().do()))
        tasks.append(asyncio.create_task(self.ensure_required_info().do()))
        await asyncio.gather(*tasks)

        self.state.analyze_query = NLWebHandlerState.DONE
        self.state.query_relevance = NLWebHandlerState.DONE
        self.state.required_info = NLWebHandlerState.DONE
        self.state.memory_items = NLWebHandlerState.DONE
        print(f"prepare tasks done")
    
    def detect_memory_items(self):
        return memory.Memory(self)
    
    def ensure_required_info(self):
        return required_info.RequiredInfo(self)
        
    def retrieve_items(self, query):
        return retriever.MilvusQueryRetriever(query, self)
    
    def get_analyze_query(self):
        return analyze_query.AnalyzeQuery(self)
    
    def get_relevance_detection(self):
        return relevance_detection.RelevanceDetection(self)
    
    async def post_prepare_tasks(self):
        await post_prepare.PostPrepare(self).do()
    
    async def get_ranked_answers(self):
        if (self.abort_fast_track):
            try:
                return await ranking.Ranking(self, self.final_retrieved_items, ranking.Ranking.POST_DECONTEXTUALIZATION).do()
            except Exception as e:
                print(f"Error in get_ranked_answers: {e}")
                traceback.print_exc()


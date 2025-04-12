from state import NLWebHandlerState
import ranking

class FastTrack:
    def __init__(self, handler):
        self.handler = handler
        
    async def do(self):
        if (self.handler.context_url != ''):
            print("Context url is not empty, skipping fast track")
            return
        items = await self.handler.retrieve_items(self.handler.query).do()
        self.handler.retrieved_items = items
        if (self.handler.state.decontextualization == NLWebHandlerState.DONE):
            if (self.handler.requires_decontextualization):
                #nvm, decontextualization required. That would have kicked off another retrieval
                return
            else:
                print(f"Decontextualized Query: {self.handler.decontextualized_query}. Requires decontextualization: {self.handler.requires_decontextualization}")
                print("Kicking off ranking after decontextualization")
                self.handler.fastTrackRanker = ranking.Ranking(self.handler, items, ranking.Ranking.POST_DECONTEXTUALIZATION)
                await self.handler.fastTrackRanker.do()
                return  
        else:
            print("Kicking off ranking before decontextualization")
            self.handler.fastTrackRanker = ranking.Ranking(self.handler, items, ranking.Ranking.FAST_TRACK)
            await self.handler.fastTrackRanker.do()
            return  
        
    
    
    

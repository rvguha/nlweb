from state import NLWebHandlerState
import ranking

class FastTrack:
    def __init__(self, handler):
        self.handler = handler
        
    async def do(self):
        items = await self.handler.retrieve_items(self.handler.query).do()
        self.handler.retrieved_items = items
        if (self.handler.state.decontextualization == NLWebHandlerState.DONE):
            if (self.handler.requires_decontextualization):
                #nvm, decontextualization required. That would have kicked off another retrieval
                return
            else:
                print("Kicking off ranking after decontextualization")
                self.handler.fastTrackRanker = ranking.Ranking(self.handler, items, ranking.Ranking.POST_DECONTEXTUALIZATION)
                await self.handler.fastTrackRanker.do()
                return  
        else:
            print("Kicking off ranking before decontextualization")
            self.handler.fastTrackRanker = ranking.Ranking(self.handler, items, ranking.Ranking.FAST_TRACK)
            await self.handler.fastTrackRanker.do()
            return  
        
    
    
    

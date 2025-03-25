

class NLWebHandlerState:

    INITIAL = 0
    IN_PROGRESS = 1
    DONE = 2

    def __init__(self, handler):
        self.handler = handler
        self.decontextualization = self.__class__.INITIAL
        self.initial_retrieval = self.__class__.INITIAL
        self.query_relevance = self.__class__.INITIAL
        self.secondary_retrieval = self.__class__.INITIAL
        self.required_info = self.__class__.INITIAL
        self.memory_items = self.__class__.INITIAL
        self.ranking = self.__class__.INITIAL
        self.analyze_query = self.__class__.INITIAL
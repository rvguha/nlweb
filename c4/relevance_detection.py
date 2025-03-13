import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json
from prompts import find_prompt, fill_prompt

class RelevanceDetection:

    RELEVANCE_PROMPT = ["""The user is querying the site {request.site} which has information about {site.itemType}s.
      Is the content on the site anyway relevant to the user's query? The user's query is: {request.query}.""",

      {"site_is_irrelevant_to_query": "True or False",
      "explanation_for_irrelevance": "Explanation for why the site is irrelevant"}]

    RELEVANCE_PROMPT_NAME = "DetectIrrelevantQueryPrompt"

    def get_prompt(self):
        item_type = self.handler.item_type
        site = self.handler.site
        prompt_str, ans_struc = find_prompt(site, item_type, self.RELEVANCE_PROMPT_NAME)

        if (prompt_str is None):
            prompt_str, ans_struc = self.RELEVANCE_PROMPT
        return prompt_str, ans_struc

    def __init__(self, handler):
        self.handler = handler

    async def do(self):
        prompt_str, ans_struc = self.get_prompt()
        prompt = fill_prompt(prompt_str, self.handler)
        print(prompt)
        response = await mllm.get_structured_completion_async(prompt, ans_struc, "gpt-4o")
        self.site_is_irrelevant_to_query = response["site_is_irrelevant_to_query"]
        self.explanation_for_irrelevance = response["explanation_for_irrelevance"]
        if (self.site_is_irrelevant_to_query == "True"):
            print(f"site is irrelevant to query: {self.explanation_for_irrelevance}")
            message = {"message_type": "site_is_irrelevant_to_query", "explanation_for_irrelevance": self.explanation_for_irrelevance}
            self.handler.query_is_irrelevant = True
            self.handler.query_done = True
            await self.handler.http_handler.write_stream(message)
        else:
            print(f"site is relevant to query: {self.explanation_for_irrelevance}")
            self.handler.query_is_irrelevant = False
            
import mllm
import retriever
import asyncio
import json
import utils
from trim import trim_json


type_to_task_map = {
    "all": ["disambiguation", "item_list_vs_property", "item_type_match"]
    "Recipe": ["diet_restriction"],
    "RealEstateListing": ["location_detection"]
}

def analysisTaskListFromTypes(types):
    task_list = []
    for t in types:


from typing_extensions import TypedDict
from typing import List

class GraphState(TypedDict):
  """
  Represents the state of our graph.

  Attributes:
   initial_question: question
   tools: list of tools
   scope: scope of the information gathered
   question_categories: question categories (n)
   num_steps: number of steps
  """
  initial_question: str
  tools: List[str]
  scope: object
  question_categories: List[str]
  categories_to_process: List[str]
  num_steps: int
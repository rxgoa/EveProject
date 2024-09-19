from langchain_core.output_parsers import JsonOutputParser
from prompts.prompts import prompt_category_graph as prompt
from llm.groq import GROQ_LLM
from langgraph.graph import StateGraph, END
from tools.graph_state import GraphState

class GraphTool:
  def __init__(self):
    self.question_category_generator =  prompt | GROQ_LLM | JsonOutputParser()
    self.workflow = StateGraph(GraphState)
    self.app = None
    self.add_nodes()
    self.set_entry_point("categorize_question")
    self.add_conditional_edges()
    self.add_edges()
    self.compile()

  def compile(self):
    self.app = self.workflow.compile()

  def get_graph(self):
    return self.app

  def invoke(self, input):
    return self.app.invoke(input)

  def state_printer(self, state):
    print("--------FINISHED STATES--------")
    print(f"Initial question: {state["initial_question"]}")
    print(f"Categories for the question: {state["question_categories"]}")
    print(f"Categories to process: {state["categories_to_process"]}")
    print(f"Steps: {state["num_steps"]}")
    print("-------------------------------")
    return

  def categorize_question(self, state):
   question = state["initial_question"]
   tools = state["tools"]
   steps = state["num_steps"]
   steps +=1

   question_categories_generator = self.question_category_generator.invoke({"initial_question": question, "tools": tools})
   print(f"\ncategories indetified: {question_categories_generator}\n")
   state["categories_to_process"] = question_categories_generator["categories"].copy()
   state["question_categories"] = question_categories_generator["categories"].copy()
   categories_to_process = state["categories_to_process"]
   return {
     "question_categories": question_categories_generator["categories"],
     "scope": question_categories_generator,
     "num_steps": steps,
     "categories_to_process": categories_to_process,
     "question_categories": state["question_categories"]
     }

  def server_information(self, state):
    print(f"server_information node called!")
    print(f"categories yet to be processed: {state["categories_to_process"]}")
    steps = state["num_steps"]
    steps +=1
    state["num_steps"] = steps
    return state

  def members_information(self, state):
    print(f"members_information node called!")
    print(f"categories yet to be processed: {state["categories_to_process"]}")
    steps = state["num_steps"]
    steps +=1
    state["num_steps"] = steps
    return state

  def final_response(self, state):
    print(f"final_response node called!")
    print(f"categories yet to be processed: {state["categories_to_process"]}")
    steps = state["num_steps"]
    steps += 1
    state["num_steps"] = steps
    return state

  ## this is just a test. for later we should expand this router or break into a few (learn more about it)
  def router_node_question(self, state):
    """
    Route question.
    Args:
     state(dict): The current graph state
    Returns:
     str: Next node to call
    """
    categories_to_process = state["categories_to_process"]

    if "server_information" in categories_to_process:
      categories_to_process.remove("server_information")
      return "server_information"
    elif "members_information" in categories_to_process:
      categories_to_process.remove("members_information")
      return "members_information"
    elif "final_response" in categories_to_process:
      categories_to_process.remove("final_response")
      return "final_response"
    else:
      return "final_response"

  def router_node_server_information(self, state):
    """
    Route question.
    Args:
     state(dict): The current graph state
    Returns:
     str: Next node to call
    """
    categories_to_process = state["categories_to_process"]

    if "members_information" in categories_to_process:
      categories_to_process.remove("members_information")
      return "members_information"
    elif "final_response" in categories_to_process:
      categories_to_process.remove("final_response")
      return "final_response"
    else:
      return "final_response"

  def router_node_members_information(self, state):
    """
    Route question.
    Args:
     state(dict): The current graph state
    Returns:
     str: Next node to call
    """
    categories_to_process = state["categories_to_process"]

    if "members_information" in categories_to_process:
      categories_to_process.remove("members_information")
      return "members_information"
    else:
      return "final_response"

  def add_nodes(self):
    self.workflow.add_node("categorize_question", self.categorize_question)
    self.workflow.add_node("state_printer", self.state_printer)
    self.workflow.add_node("server_information", self.server_information)
    self.workflow.add_node("members_information", self.members_information)
    self.workflow.add_node("final_response", self.final_response)

  def set_entry_point(self, entry_point: str):
    self.workflow.set_entry_point(entry_point)

  def add_conditional_edges(self):
    # conditional edges
    self.workflow.add_conditional_edges(
      "categorize_question",
      self.router_node_question,
      {
        "server_information": "server_information",
        "members_information": "members_information",
        "final_response": "final_response"
      }
    )

    self.workflow.add_conditional_edges(
      "server_information",
      self.router_node_server_information,
      {
        "members_information": "members_information",
        "final_response": "final_response"
      }
    )

    self.workflow.add_conditional_edges(
      "members_information",
      self.router_node_members_information,
      {
        "final_response": "final_response"
      }
    )

  def add_edges(self):
    self.workflow.add_edge("final_response", "state_printer")
    self.workflow.add_edge("state_printer", END)



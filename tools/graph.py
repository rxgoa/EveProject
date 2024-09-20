import json
from langchain_core.output_parsers import JsonOutputParser
from datetime import datetime
from discord import BaseActivity, Spotify
from typing import List
from prompts.prompts import prompt_category_graph as prompt
from cache.custom_cache import cache
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

  async def ainvoke(self, input):
    return await self.app.ainvoke(input)

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

  def get_interaction_scope(self, interaction):
    return self._get_interaction_scope(interaction)

  def get_all_info_server(self, guild):
      return self._get_all_info_server(guild)

  def get_all_members(self, members):
      return self._get_all_members(members)

  def get_all_channels(self, channels):
      return self._get_all_channels(channels)

  def server_information(self, state):
    print(f"server_information node called!")
    print(f"categories yet to be processed: {state["categories_to_process"]}")
    steps = state["num_steps"]
    steps +=1
    state["num_steps"] = steps
    interaction_scope = self._get_interaction_scope()
    guild = interaction_scope.guild
    # we need to format channels just like members
    # because of discord types etc
    #channels = self._get_all_channels()

    channels = [channel.name for channel in guild.channels]

    server_info = {
        "name": guild.name,
        "id": guild.id,
        "owner": guild.owner.name if guild.owner else "Unknown",
        "member_count": guild.member_count,
        "channels": channels,
        "members": []
    }

    state["scope"]["server_info"] = server_info

    return state

  def members_information(self, state):
    print(f"members_information node called!")
    print(f"categories yet to be processed: {state["categories_to_process"]}")
    steps = state["num_steps"]
    steps +=1
    state["num_steps"] = steps

    interaction_scope = self._get_interaction_scope()
    guild = interaction_scope.guild
    members = self._get_all_members(guild.members)
    state["scope"]["members_information"] = members

    return state

  def final_response(self, state):
    print(f"final_response node called!")
    print(f"categories yet to be processed: {state["categories_to_process"]}")
    steps = state["num_steps"]
    steps += 1
    state["num_steps"] = steps
    with open("final_response.json", "w") as file:
      state["interaction"] = "removed because we cant serialize interaction type"
      json.dump(state, file)
    #return state
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
    elif "channel_information_by_name" in categories_to_process:
      categories_to_process.remove("channel_information_by_name")
      return "channel_information_by_name"
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

  def _get_all_info_server(self, guild = None):
      if "get_all_info_server" in cache or guild is None:
          return cache["get_all_info_server"]

      cache.set_with_ttl("get_all_info_server", guild, 60)
      return guild

  def _get_interaction_scope(self, interaction: List[object] = None):
    if "get_interaction_scope" in cache or interaction is None:
        return cache["get_interaction_scope"]

    cache.set_with_ttl("get_interaction_scope", interaction, 60)
    return interaction

  def channel_information_by_name(self, state):
    name = None
    if state["scope"]["categories_scope"]:
      channel_name_scope = state["scope"]["categories_scope"]["channel_information_by_name"]
      if isinstance(channel_name_scope, list):
       # TODO: make logic where there is more than one name
       for i in channel_name_scope:
         name = i["channel_name"]
      else:
        name = channel_name_scope["channel_name"]
    else:
      name = "INVALID_CHANNEL_NAME"

    channels = self._get_all_channels()
    for channel in channels:
        if channel["name"] in name.lower():
            iso_format = channel["created_at"].isoformat() if isinstance(channel["created_at"], datetime) else channel["created_at"]
            channel["created_at"] = iso_format
            state["scope"]["channel_information_by_name"] = channel
            return state

  async def channel_history_information_by_id(self, state):
     interaction_scope = self._get_interaction_scope()
     id = state["scope"]["channel_information_by_name"]["id"]

     channel = interaction_scope.client.get_channel(int(id))
     messages = []
     async for message in channel.history(limit=100, oldest_first=True):
         messages.append({
           "author": f"{message.author}",
           "channel_name": f"{message.channel.name}",
           "content": f"{message.content}"
         })

     state["scope"]["channel_history_information_by_id"] = messages
     state["categories_to_process"].remove("channel_history_information_by_id")

     return state

  def channel_information_list(self, state):
    state["scope"]["channel_information_list"] = state["scope"]["server_info"]["channels"]
    return state

  def _get_all_channels(self, channels=None):
     if "get_all_channels" in cache or channels is None:
         return cache["get_all_channels"]

     channels_server = []
     for channel in channels:
         channels_server.append({
             "id": channel.id,
             "category": {
                 "nsfw": channel.category.nsfw,
                 "name": channel.category.name
             } if channel.category is not None else None,
             "changed_roles": channel.changed_roles,
             "created_at": channel.created_at,
             "jump_url": channel.jump_url,
             "mention": channel.mention,
             "name": channel.name
         })
     cache.set_with_ttl("get_all_channels", channels_server, 1200)
     return channels_server

  def _get_all_members(self, members):
    if "get_all_members" in cache:
        return cache["get_all_members"]

    members_data = []

    for member in members:
        member_info = {
            "id": member.id,
            "name": member.name,
            "display_name": member.display_name,
            "avatar": {
                "url": member.avatar.url,
                "key": member.avatar.key
            } if member.avatar is not None else None,
            "status": member.status.name,
            "raw_status": member.raw_status,
            "bot": member.bot,
            "activities": [],
            "roles": [role.name for role in member.roles],
        }

        for activity in member.activities:
            if isinstance(activity, Spotify):
                member_info["activities"].append({
                    "type": activity.type.name,
                    "title": activity.title,
                    "artists": activity.artists,
                    "track_url": activity.track_url,
                    "track_id":activity.track_id,
                    "album_cover_url": activity.album_cover_url,
                    "value": f"{member.display_name} is listening to {activity.title} by {', '.join(activity.artists)} on Spotify."
                })
            elif isinstance(activity, BaseActivity):
                member_info["activities"].append({
                    "type": activity.type.name,
                    "value": f"{activity.name}",
                    "url": activity.url if hasattr(activity, 'url') and activity.url else None,
                    "details": activity.details if hasattr(activity, 'details') and activity.details else None,
                })
        members_data.append(member_info)

    cache.set_with_ttl("get_all_members", members_data, 60)
    return members_data

  def add_nodes(self):
    self.workflow.add_node("categorize_question", self.categorize_question)
    self.workflow.add_node("state_printer", self.state_printer)
    self.workflow.add_node("server_information", self.server_information)
    self.workflow.add_node("members_information", self.members_information)
    self.workflow.add_node("channel_information_list", self.channel_information_list)
    self.workflow.add_node("channel_history_information_by_id", self.channel_history_information_by_id)
    self.workflow.add_node("channel_information_by_name", self.channel_information_by_name)
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
        "channel_information_by_name": "channel_information_by_name",
        "final_response": "final_response",
        "channel_information_list": "channel_information_list"
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
    self.workflow.add_edge("channel_information_by_name", "channel_history_information_by_id")
    self.workflow.add_edge("channel_history_information_by_id", "final_response")
    self.workflow.add_edge("channel_information_list", "final_response")
    self.workflow.add_edge("final_response", "state_printer")
    self.workflow.add_edge("state_printer", END)



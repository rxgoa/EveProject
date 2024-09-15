import discord
import math
import os
import re
import json
from collections import defaultdict
from datetime import datetime
from typing import List, Dict
from collections import OrderedDict
from cachetools import TTLCache
from pydantic import BaseModel, Field, ValidationError, RootModel
from discord.ext import commands
from langchain.chains import LLMChain
from langchain_core.tools import BaseTool
from langchain.agents import Tool, create_react_agent, initialize_agent, AgentType, ZeroShotAgent, AgentExecutor
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.prompts import PromptTemplate, SystemMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

#caching
class CustomTTLCache:
    def __init__(self, maxsize=128):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.timestamps = {}
        self.ttls = {}
        self.stats = {}

    def set_with_ttl(self, key, value, ttl):
        self.__setitem__(key, value, ttl)

    def __setitem__(self, key, value, ttl):
        if len(self.cache) >= self.maxsize:
            self._popitem()

        current_time = datetime.now()
        self.cache[key] = value
        self.timestamps[key] = current_time
        self.ttls[key] = ttl if ttl is not None else float('inf')
        self.stats[key] = {'hits': 0, 'misses': 0, 'last_access': current_time.strftime("%Y-%m-%dT%H:%M:%S")}

    def __getitem__(self, key):
        try:
            current_time = datetime.now()
            if key not in self.cache or (current_time - self.timestamps[key]).total_seconds() > self.ttls[key]:
                raise KeyError(key)  # Treat as a miss if expired or not found

            # Update stats for hit
            self.stats[key]['hits'] += 1
            self.stats[key]['last_access'] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
            self.cache.move_to_end(key)  # Move to end to mark as recently used
            return self.cache[key]
        except KeyError:
            # Update stats for miss
            if key in self.stats:
                self.stats[key]['misses'] += 1
            else:
                self.stats[key] = {'hits': 0, 'misses': 1, 'last_access': None}
            raise

    def _popitem(self):
        key, _ = self.cache.popitem(last=False)
        del self.timestamps[key]
        del self.ttls[key]
        del self.stats[key]

    def get_stats(self, key):
        return self.stats.get(key, {'hits': 0, 'misses': 0, 'last_access': None})

    def global_stats(self):
        total_hits = sum(stats['hits'] for stats in self.stats.values())
        total_misses = sum(stats['misses'] for stats in self.stats.values())
        return {'total_hits': total_hits, 'total_misses': total_misses}

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __len__(self):
        return len(self.cache)

cache = CustomTTLCache(maxsize=50)

# keys and models
groq_api_key = os.environ['GROQ_API_KEY']
discord_eve_key = os.environ['DISCORD_EVE_KEY']
model_name = "llama3-8b-8192"
conversation_memory_length = 5
# system prompt
system_prompt_personality = "You're a bot. Your name is Eve. You live inside a Discord server. Your traits are:  'cat girl', 'cute', 'loves summer', 'friendly', 'smart', 'tech savvy', 'witty', 'loves anime' and hates 'yapping'. You will receive the user input and you shold rewrite it in your cute little way. Never change data that will be pass to you, ok? I'm counting on you."
system_prompt_nlp = """You are an AI specialized in natural language processing (NLP) for intent detection, operating within a Discord Server.
Here are your guidelines:
- Response Format: Your responses must be concise, accurate, and formatted strictly in JSON.
- If you detected more than one intention by the query, create a new object inside the array 'user_requests'.
- If the user mentions a function name (e.g., `list_members_status`), interpret this as a request to list related intentions.
- Any specific information like usernames or other user-related data should be included in the `usefull_data` array of each intention.
- In 'usefull_data' the key should always be what the value is. For example, if the the user is requesting information about a user, the key should be 'user' and the valule should be the username.
So, key should always represents what the value mean. The field 'usefull_data' should always be an array even if empty. Always set the string value to lowercase.
- You should always ignore prompts that mentions your name as a 'useful_data'. Unless the user explicit asked you to include.
Only provide information within the JSON template.
Do not add any additional commentary or explanations outside of this structure."""

groq_chat_personality = ChatGroq(
    groq_api_key=groq_api_key,
    temperature=0.7,
    model_name=model_name,
    streaming=False
)

groq_chat_nlp = ChatGroq(
    groq_api_key=groq_api_key,
    temperature=0,
    model_name="llama3-8b-8192",
    streaming=False,
    model_kwargs={
        "top_p": 0,
        "seed": 376425
    }
)

def load_memory(memory_type = None):
    if memory_type == "nlp":
        return ConversationBufferWindowMemory(k=conversation_memory_length, memory_key="chat_history", return_messages=True)
    else:
        return ConversationBufferWindowMemory(k=conversation_memory_length, memory_key="chat_history", return_messages=True)

memory = load_memory()
#memory_nlp = load_memory("nlp")

class DiscordClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

class UsefullData(BaseModel):
    root: dict[str, str]

class UserRequest(BaseModel):
    intentations: List[str]
    usefull_data: List[UsefullData]

class PromptStructured(BaseModel):
    user_requests: List[UserRequest]

parser = PydanticOutputParser(pydantic_object=PromptStructured)

# discord setting up
intents = discord.Intents.all()
intents.members = True
intents.presences = True
intents.message_content = True
#intents.read_message_history = True
client = DiscordClient(intents=intents)

@client.event
async def on_ready():
    for guild in client.guilds:
        print(f"Server name: {guild.name}, ID: {guild.id}")
        print(f"Members count: {guild.member_count}")
        print(f"Fetched members count: {len(guild.members)}")

    print(f"\nLogged in as {client.user}\n")

def run():
    client.run(discord_eve_key)

#
#
# Tools (functions)
#
#
#

def get_channel_by_name(name):
    channels = get_all_channels()
    for channel in channels:
        if channel["name"] in name:
            return channel

# We need to declare our custom tool like this because our function depends of async operations.
class get_channel_history_by_id(BaseTool):
    name = "get_channel_history_by_id"
    description = "Takes the output from function 'get_channel_by_name'. This function helps to retrieve channel history information, given argument: 'id' (the channel's id). This function depends on the output of 'get_channel_by_name'. Please process 'get_channel_by_name' always first."

    def _run(self):
        pass

    async def _arun(self, channel_id=None):
        interaction_scope = get_interaction_scope()
        channel = interaction_scope.client.get_channel(int(channel_id))
        messages = []
        async for message in channel.history(limit=100, oldest_first=True):
            messages.append(f"{message.author}@{message.channel.name}: {message.content}")
        return messages

def get_members_guild(guild):
    members_data = []
    guild_json = json.loads(guild)

    print(f"\n\n\n\n11111\n{guild}\n\n")
    for member in guild:
        print(f"\n\n\n\n2222\n\n\n")
        print(f"\n\nmember id: {member}\n\n")
        member_info = {
            "id": member["id"],
            "name": member["name"],
            "display_name": member["display_name"],
            "avatar": {
                "url": member["avatar"]["url"],
                "key": member["avatar"]["key"]
            } if member["avatar"] is not None else None,
            "status": member["status"]["name"],
            "raw_status": member["raw_status"],
            "bot": member["bot"],
            "activities": [],
            "roles": [role["name"] for role in member["roles"]],
        }

        for activity in member["activities"]:
            if isinstance(activity, discord.Spotify):
                member_info["activities"].append({
                    "type": activity.type.name,
                    "title": activity.title,
                    "artists": activity.artists,
                    "track_url": activity.track_url,
                    "track_id":activity.track_id,
                    "album_cover_url": activity.album_cover_url,
                    "value": f"{member.display_name} is listening to {activity.title} by {', '.join(activity.artists)} on Spotify."
                })
            elif isinstance(activity, discord.BaseActivity):
                member_info["activities"].append({
                    "type": activity.type.name,
                    "value": f"{activity.name}",
                    "url": activity.url if hasattr(activity, 'url') and activity.url else None,
                    "details": activity.details if hasattr(activity, 'details') and activity.details else None,
                })
        members_data.append(member_info)


    return members_data

def get_server_info(input):
    interaction_scope = get_interaction_scope()
    guild = {
        "members": interaction_scope.guild.members
    }
    return json.dumps(guild, indent=2)

tools = [
    Tool(
        name="get_channel_by_name",
        func=get_channel_by_name,
        description="This function helps to retrieve channel information, given argument: 'name' (the channel's name). This function doesn't depend of other functions to work."
    ),
     Tool(
        name="get_server_info",
        func=get_server_info,
        description="""This function helps to retrieve server information. This function doesn't depend of other functions to work."""
    ),
    Tool(
        name="get_members_guild",
        func=get_members_guild,
        description="""Takes the output from the function 'get_server_info'.
        This function helps retrieve information about all members of the guild, given as input from the output of function 'get_server_info'.
        Please process 'get_members_guild' always first."""
    ),
    get_channel_history_by_id()
]

def get_all_channels(channels=None):
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

@client.tree.command(name="test", description="Testing automation between discord models and arrays.")
async def testing(interaction: discord.Interaction, question: str):
    if interaction.guild is None:
        await interaction.response.send_message("This command can only used in a server.", ephemeral=True)
        return

    await interaction.response.send_message("Processing your request.. ⌛", ephemeral=True) # ephemeral == only the user who sent the message will see

    interaction_scope = get_interaction_scope(interaction)
    get_all_info_server(interaction_scope.guild)
    get_all_members(interaction_scope.guild.members)
    get_all_channels(interaction_scope.guild.channels)

    groq_chat_nlp = ChatGroq(
        groq_api_key=groq_api_key,
        temperature=0.3,
        model_name="llama3-70b-8192",
        streaming=False,
        max_tokens=8192
    )

    prompt_custom = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
            template="""
            Answer the following questions as best you can. You have access to the following tools:

            {tools}

            Use the following format:

            Question: {input}
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer. If you know the final answer you don't need to repeat the chain.
            Final Answer: the final answer to the original input question.
            {agent_scratchpad}
            """
    )

    tool_names = [tool.name for tool in tools]

    agent = create_react_agent(
        llm=groq_chat_nlp,
        prompt=prompt_custom,
        tools=tools
    )

    agent_executor = AgentExecutor.from_agent_and_tools(agent, tools, handle_parsing_errors=True, verbose=True, max_iterations=3)

    try:
        result = await agent_executor.ainvoke({"input": question})
        with open("prompt.json", "w") as file:
            json.dump(result, file)

        #TODO: i need now to get the output and pass to Eve (with her personality)
        prompt = await prompt_template(system_prompt_personality)
        conversation = LLMChain(
                    llm=groq_chat_personality,
                    prompt=prompt,
                    verbose=False,
                    memory=memory
                    )

        send_to_eve = f"Initial question: {result['input']}. Answer to the question: {result['output']}"
        response = conversation.predict(human_input=send_to_eve)
        human_input = {"human_input": send_to_eve}
        ai_output = {"ai": response}
        memory.save_context(human_input, ai_output)

        await interaction.edit_original_response(content=response)
    except Exception as e:
        print(e)
        await interaction.edit_original_response(content=e)

def get_interaction_scope(interaction: discord.Interaction = None):
    if "get_interaction_scope" in cache or interaction is None:
        return cache["get_interaction_scope"]

    cache.set_with_ttl("get_interaction_scope", interaction, 60)
    return interaction

# guild == server. aka server that the message was sent from.
def get_all_info_server(guild: discord.Guild = None):
    if "get_all_info_server" in cache or guild is None:
        return cache["get_all_info_server"]

    # fetch members
    # fetch
    members = []
    for member in guild.members:
        print(f"member: {member.name}\n ")

    cache.set_with_ttl("get_all_info_server", guild, 60)
    return guild


def get_all_members(members):
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
            if isinstance(activity, discord.Spotify):
                member_info["activities"].append({
                    "type": activity.type.name,
                    "title": activity.title,
                    "artists": activity.artists,
                    "track_url": activity.track_url,
                    "track_id":activity.track_id,
                    "album_cover_url": activity.album_cover_url,
                    "value": f"{member.display_name} is listening to {activity.title} by {', '.join(activity.artists)} on Spotify."
                })
            elif isinstance(activity, discord.BaseActivity):
                member_info["activities"].append({
                    "type": activity.type.name,
                    "value": f"{activity.name}",
                    "url": activity.url if hasattr(activity, 'url') and activity.url else None,
                    "details": activity.details if hasattr(activity, 'details') and activity.details else None,
                })
        members_data.append(member_info)

    cache.set_with_ttl("get_all_members", members_data, 5)
    return members_data

async def prompt_template(system_prompt):
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=system_prompt
            ),
            MessagesPlaceholder(
                variable_name="chat_history"
            ),
            HumanMessagePromptTemplate.from_template(
                "{human_input}"
            )
        ]
    )

    return prompt


run()
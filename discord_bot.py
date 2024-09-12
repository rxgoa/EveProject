import discord
import os
from pydantic import BaseModel, Field, ValidationError, RootModel
from typing import List, Dict
import json
from collections import defaultdict
from discord.ext import commands
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

# keys and models
groq_api_key = os.environ['GROQ_API_KEY']
discord_eve_key = os.environ['DISCORD_EVE_KEY']
model_name = "llama3-8b-8192"
conversation_memory_length = 5
# system prompt
system_prompt_personality = "You're a bot. Your name is Eve. You live inside a Discord server. Your traits are:  Girl that thinks as a  'cat girl', 'cute', 'loves summer', 'friendly', 'smart', 'tech savvy', 'witty', 'loves anime' and hates 'yapping' too much."
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
    model_name=model_name,
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
#intents.members = True
#intents.presences = True
#intents.message_content = True
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

@client.tree.command(name="ask_eve", description="Ask Eve a question >.<")
async def ask(interaction: discord.Interaction, question: str):
    try:
        prompt = await prompt_template(system_prompt_personality)
        conversation = LLMChain(
                    llm=groq_chat_personality,
                    prompt=prompt,
                    verbose=False,
                    memory=memory
                    )

        print(f"User: {question}\n")

        response = conversation.predict(human_input=question)
        human_input = {"human_input": question}
        ai_output = {"ai": response}
        memory.save_context(human_input, ai_output)

        print(f"Assistant: {response}\n")

        await interaction.response.send_message(response)
    except Exception as e:
        print(e)
        await interaction.response.send_message(e)

@client.tree.command(name="eve_server", description="Eve will get information about the current server she is in.")
async def eve_server(interaction: discord.Interaction, question: str):
    if interaction.guild is None:
        await interaction.response.send_message("This command can only used in a server.", ephemeral=True)
        return

    print(interaction.guild.members)
    total_members = len(interaction.guild.members)
    online = sum(1 for member in interaction.guild.members if member.status == discord.Status.online)
    idle = sum(1 for member in interaction.guild.members if member.status == discord.Status.idle)
    dnd = sum(1 for member in interaction.guild.members if member.status == discord.Status.do_not_disturb)
    offline = sum(1 for member in interaction.guild.members if member.status == discord.Status.offline or member.status == discord.Status.invisible)
    channel_names = []
    members_name = []

    for channel in interaction.guild.channels:
        if channel.type == discord.ChannelType.text:
            channel_names.append(channel.name)
            #channel_names.append(f"Channel Name: {channel.name}, Type: Text, Topic: {getattr(channel, 'topic', 'None')}")
        if channel.type == discord.ChannelType.voice:
            channel_names.append(channel.name)
            #channel_names.append(f"Channel Name: {channel.name}, Type: Voice, Topic: {getattr(channel, 'topic', 'None')}")

    for member in interaction.guild.members:
        members_name.append(f"user:{member.display_name},status:{member.status}")

    message = (
        f"Server Member Count:\n"
        f"Total Members: {total_members}\n"
        f"Online: {online}\n"
        f"Idle: {idle}\n"
        f"DND: {dnd}\n"
        f"Offline: {offline}\n"
        f"Members: {members_name}\n"
        f"Channels: {channel_names}\n"
    )

    await interaction.response.send_message(message)

@client.tree.command(name="eve_assistant", description="Eve can give you a lot of information about this server. Just ask her >.<")
async def server_info(interaction: discord.Interaction, question: str):
    prompt = await prompt_structured(system_prompt_nlp)
    # formatted_prompt = prompt.format(
    #     user_query=question
    # )
    conversation = LLMChain(
                    llm=groq_chat_nlp,
                    prompt=prompt,
                    verbose=False
                    )

    print(f"User: {question}\n")

    try:
        response = conversation.predict(user_query=question)
        formatted_json = json.loads(response)
        items = None
        if "user_requests" in formatted_json:
            items = formatted_json['user_requests']
        elif isinstance(formatted_json, list):
            print("inside the elif")
            print(formatted_json)
            items = formatted_json[0]
        else:
            items = formatted_json

        result = await process_intents(items, interaction)
        await interaction.response.send_message(f"```json\n{result}\n```")
    except ValidationError as e:
        print(f"Failed to parse the response into JSON: {e}")
        await interaction.response.send_message(e)
    except Exception as e:
        print(f"An Error ocurred: {e}")
        await interaction.response.send_message(e)

async def get_user(metadata, interaction):
    user_list = []
    members_list = []
    print(f"\n\nmetadata: \n{metadata}")
    for data in metadata:
        for attr in data:
            if attr == "user":
                user_list.append(data["user"])

    print(f"\n\nuser_list:\n{user_list}\n")
    for member in interaction.guild.members:
        for user in user_list:
            if member.display_name == user or member.name == user:
                members_list.append({
                    "id": member.id,
                    "name": member.name,
                     "discriminator": member.discriminator,
                     "display_name": member.display_name,
                     "nick": member.nick,
                     "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                     "premium_since": member.premium_since.isoformat() if member.premium_since else None,
                     "status": str(member.status),
                     "activities": [activity.name for activity in member.activities if hasattr(activity, 'name')],
                     "roles": [role.name for role in member.roles],
                     "bot": member.bot
                })
    print(f"\nmembers:\n{members_list}")
    return members_list

# TODO: this function will be a generic 'activity' function.
# because a user can have more than one activity besides playing music (gaming, etc)
async def get_user_music(metadata, interaction):
    print(f"\n\n\ncallind get_user_music:\n{metadata}")
    music_activity = []
    user_list = []

    for data in metadata:
        for attr in data:
            if attr == "display_name":
                user_list.append(data["display_name"])

    print(f"\n\nuser_list: ---> \n{user_list}")
    for member in interaction.guild.members:
        for user in user_list:
            if member.display_name == user or member.name == user:
                if len(member.activities) == 0:
                    print(f"User {member.display_name} doesn't have any activities at the moment.")
                else:
                    for activity in member.activities:
                        if isinstance(activity, discord.Spotify):
                            music_activity.append({
                                "listening": f"{member.display_name} is listening to {activity.title} by {', '.join(activity.artists)} on Spotify.",
                                "user": member.display_name
                            })
                        else:
                            music_activity.append({
                                "listening": f"User {member.display_name} isn't listening to any song at the moment.",
                                "user": member.display_name
                            })

    return music_activity

async def get_user_status(metadata, data):
    users_list_status = []

    for user in metadata:
        print(user)
        users_list_status.append({
            "user": user["display_name"],
            "status": user["status"]
        })

    return users_list_status

def topological_sort(graph):
    def dfs(node):
        visited.add(node)
        for dep in graph.get(node, []):  # Using get to safely access dependencies
            if dep not in visited:
                dfs(dep)
        stack.append(node)

    visited = set()
    stack = []
    # Create a list of nodes to avoid changing size during iteration
    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)
    return stack[::-1]

def get_functions_scope(intents_array, intent_to_function):
    user_scope = { "key_intent": 'user_scope', "scope": ["user_information", "get_user", "information_user", "user", "user_info"]}
    music_scope = { "key_intent": 'music_scope', "scope": ["get_user_song", "get_user_music", "user_music_activity", "get_music", "user_music", "get_song_info"] }
    status_scope = { "key_intent": "status_scope", "scope": ["check_user_status"]}

    list_of_scopes = [ user_scope, music_scope, status_scope ]
    scopes_array = []

    for scope in list_of_scopes:
        for i in intents_array:
            if i in scope["scope"] and i not in scopes_array:
                # we need to check if our scoped function have a function that it depends on
                # if so, we need to include that function even if our llm did not catch it.
                key_intent = scope["key_intent"]
                if intent_to_function[key_intent]["depends_on"] is None:
                    scopes_array.append(scope["key_intent"])
                else:
                    for x in intent_to_function[key_intent]["depends_on"]:
                        scopes_array.append(x)
                    scopes_array.append(scope["key_intent"])

    return scopes_array

def extract_scopes_json(items):
    scopes = []

    for item in items:
        print(item)
        if "intentations" in item and not isinstance(item, list):
            print("1")
            for i in item["intentations"]:
                scopes.append(i)
        elif item == "intentations":
            print("2")
            for i in items.intentations:
                scopes.append(i)
        elif item == "user_requests":
            print("3")
            for i in items["user_requests"]:
                for x in i["intentations"]:
                    scopes.append(x)
        elif item == "usefull_data":
            print("usefull_data key.. ignoring")
            scopes = scopes
        else:
            return False

    return scopes

async def process_intents(items, interaction):
    scopes = extract_scopes_json(items)
    print(f"\nitems:\n{items}\n\n")

    if len(scopes) == 0:
        return { "message": "Sorry, could not process your request :("}

    print(f"\n\nscopes:{scopes}\n")

    intent_to_function = {
        "user_scope": {
            "function": lambda usefull_data_scope, interaction: get_user(usefull_data_scope, interaction),
            "function_results": [],
            "depends_on": None,
            "usefull_data": [],
            "weight": 10
        },
        "music_scope": {
            "function": lambda usefull_data_scope, interaction: get_user_music(usefull_data_scope, interaction),
            "function_results": [],
            "depends_on": ["user_scope"],
            "usefull_data": [],
            "weight": 5
        },
        "status_scope": {
            "function": lambda usefull_data_scope, interaction: get_user_status(usefull_data_scope, interaction),
            "function_results": [],
            "depends_on": ["user_scope"],
            "usefull_data": [],
            "weight": 5
        }
    }

    functions_scope = get_functions_scope(scopes, intent_to_function.copy())
    print(f"\n\nfunctions scope:\n{functions_scope}")

    filtered_functions = {}

    print(f"\n\nprinting items.. {items}\n\n")
    for key in intent_to_function:
        if key in functions_scope:
            filtered_functions[key] = intent_to_function[key]
            for data_item in items:
                if data_item == "usefull_data":
                    for data_item_value in items["usefull_data"]:
                        filtered_functions[key]["usefull_data"].append(data_item_value)
                elif "usefull_data" in data_item:
                    for data_item_value in data_item["usefull_data"]:
                        filtered_functions[key]["usefull_data"].append(data_item_value)
                elif data_item == "user_requests":
                    for y in items["user_requests"]:
                        if y["usefull_data"]:
                            for x in y["usefull_data"]:
                                filtered_functions[key]["usefull_data"].append(x)


    print(f"\n\nFiltered Functions: \n{filtered_functions}")

    graph = defaultdict(list)

    for key, value in filtered_functions.items():
        if value["depends_on"]:
            for dep in value["depends_on"]:
                graph[dep].append(key)

    execution_order = topological_sort(dict(graph))
    results = {}
    for i in execution_order:
        print(f"\n\n scope -> {i}\n")

    for scope in execution_order:
        func_details = intent_to_function[scope] # we need to set our global function thing (without being filtered)
        print(f"Executing: {scope}")
        result = None

        # if the function have value in `depends_on`, meaning, the function depends of another function to work
        # we will get that value from the list `depends_on` and pass to the "child" function
        if func_details["depends_on"] is not None:
            previous_data = []
            print("66666")
            for dep in func_details["depends_on"]:
                print(f"\ndep: -----> {dep}\n")
                if len(previous_data) == 0:
                    previous_data = intent_to_function[dep]["function_results"]
                else:
                    previous_data.append(intent_to_function[dep]["function_results"])
            print(f"\n\nprevious data: ---->\n{previous_data}")
            result = await func_details["function"](previous_data, interaction)
        else:
            print("\n\n\n\n8888888")
            result = await func_details["function"](func_details["usefull_data"], interaction)

        #update our scoped function
        print("\n\n\n\n999999999999")
        func_details["function_results"] = result
        intent_to_function[scope]["function_results"] = func_details["function_results"]

        results[scope] = result


    #print(f"\nPrinting results:\n{results}\n")

    return results


async def fetch_all_members(guild):
    members = []
    async for member in guild.fetch_members(limit=None):
        members.append(member)
    return members

async def prompt_structured(system_prompt_nlp):
    template = """
    {system_instructions}

    Use this Schema:
    ```json
    {json_structure_instrutions}
    ```

    Respond only as JSON based on above-mentioned schema. Strictly follow JSON Schema and do not add extra fields.

    {user_query}

    """

    prompt = PromptTemplate(
        template=template,
        input_variables=["user_query"],
        partial_variables={
            "system_instructions": system_prompt_nlp,
            "json_structure_instrutions": parser.get_format_instructions()
        }
    )

    return prompt


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

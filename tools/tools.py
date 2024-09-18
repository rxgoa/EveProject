from datetime import datetime
import json
from discord import Guild, Interaction, BaseActivity, Spotify
from langchain.agents import Tool
from langchain_core.tools import BaseTool
# my modules
from cache.custom_cache import cache

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

# We need to declare our custom tool like this because our function depends of async operations.
class get_channel_history_by_id(BaseTool):
    name: str ="get_channel_history_by_id"
    description: str ="""
    This function helps to retrieve channel history information, given argument: 'id' (the channel's id).
    Takes the output from function: 'get_channel_by_name'.
    This function depends on the output of 'get_channel_by_name'.
    Please process 'get_channel_by_name' always first.
    This function doesn't call other functions after being executed."""

    def _run(self):
        pass

    async def _arun(self, channel_id):
        interaction_scope = get_interaction_scope()
        print(f"\n\n\nCHANNEL_ID: {channel_id}\n\n\n\n")
        id = 0
        if "id" in channel_id:
            obj = json.loads(channel_id)
            print(f"\n\n\nid...\n")
            id = obj["id"]
        elif "name" in channel_id:
            obj = json.loads(channel_id)
            print(f"\n\n\nname...\n")
            id = obj["name"]
        else:
            print(f"\n\n\nelse...\n")
            id = channel_id

        channel = interaction_scope.client.get_channel(int(id))
        messages = []
        async for message in channel.history(limit=100, oldest_first=True):
            messages.append(f"{message.author}@{message.channel.name}: {message.content}")
        return messages

def get_channel_by_name(name):
    print(f"\n\n\n\n\n'name':\n{name}")
    channels = get_all_channels()
    for channel in channels:
        if channel["name"] in name.lower():
            iso_format = channel["created_at"].isoformat() if isinstance(channel["created_at"], datetime) else channel["created_at"]
            channel["created_at"] = iso_format
            return json.dumps(channel, indent=2)

def get_server_info(input):
    print(f"\n\n\nINPUT FOR GET_SERVER_INFO: {input}\n\n")
    interaction_scope = get_interaction_scope()
    print(f"\n\nGET_SERVER_INFO\n\n")
    guild = interaction_scope.guild
    members = get_all_members(guild.members)

    channels = [channel.name for channel in guild.channels]
    server_info = {
        "name": guild.name,
        "id": guild.id,
        "owner": guild.owner.name if guild.owner else "Unknown",
        "member_count": guild.member_count,
        "channels": channels,
        "members": members
    }

    #return json.dumps({ "server_info": server_info }, indent=2)
    return server_info

class get_members_server(BaseTool):
        name: str = "get_members_server"
        description: str ="""
        This function helps to retrieve channel members information, given argument: 'server_info'.
        Argument have the following information: name, id, owner, member_count, channels and members.
        Takes the output from function: 'get_server_info'.
        This function depends on the output of 'get_server_info'.
        Please process 'get_server_info' always first.
        This function doesn't call other functions after being executed."""

        def _run(self):
            self

        async def _arun(self, guild: Guild):
            print(f"\ncalling _arun for get_members_server!!!\n\n")
            json_guild = None
            if isinstance(guild, str):
                # TODO: this is a hacky thing to do because our model sometimes gives us some garbage string from out chain.
                # to fix this, i probably need to tweak the prompt. but for now, we do this.
                guild = guild.replace("'", '"')
                start = guild.find('{')
                end = guild.rfind('}')
                clean_str = guild[start:end+1]
                j_guild = json.loads(clean_str)
                json_guild = j_guild["server_info"]
            else:
                json_guild = guild["server_info"]

            return json.dumps({ "members": json_guild["members"] }, indent=2)

def get_interaction_scope(interaction: Interaction = None):
    print(cache)
    if "get_interaction_scope" in cache or interaction is None:
        return cache["get_interaction_scope"]

    cache.set_with_ttl("get_interaction_scope", interaction, 60)
    return interaction

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

def get_all_info_server(guild: Guild = None):
    if "get_all_info_server" in cache or guild is None:
        return cache["get_all_info_server"]

    cache.set_with_ttl("get_all_info_server", guild, 60)
    return guild

tools = [
    Tool(
        name="get_channel_by_name",
        func=get_channel_by_name,
        description="""This function helps to retrieve channel information, given argument: 'name' (the channel's name).
        This function doesn't depend of other functions to work."""

    ),
     Tool(
        name="get_server_info",
        func=get_server_info,
        description="""This function helps to retrieve server information.
        This function doesn't depend of other functions to work.
        You should only call this functions that have this function as dependencie: get_members_information_guild."""
    ),
    get_members_server(),
    get_channel_history_by_id()
]
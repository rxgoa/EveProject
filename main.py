import os
import sys
from discord import Intents
from discord.ext import commands
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DiscordClient(commands.Bot):
    def __init__(self, intents: Intents):
        super().__init__(command_prefix="!", intents=intents)

    async def setup(self):
        await self.load_cogs()

    async def on_ready(self):
        for guild in self.guilds:
            print(f"Server name: {guild.name}, ID: {guild.id}")
            print(f"Members count: {guild.member_count}")
            print(f"Fetched members count: {len(guild.members)}")
            print(f"\nLogged in as {self.user}\n")

    async def setup_hook(self):
        # always load cogs first
        print(f"Loading cogs..")
        await self.load_extension("bot.discord")
        print(f"Loading cogs finished..")
        # then always sync the tree (cogs)
        print(f"Syncing tree..")
        await self.tree.sync()
        print(f"Syncing tree finished..")

if __name__ == '__main__':
    token = os.environ['DISCORD_EVE_KEY']
    # discord setup
    intents = Intents.all()
    intents.members = True
    intents.presences = True
    intents.message_content = True
    client = DiscordClient(intents=intents)
    client.run(token)

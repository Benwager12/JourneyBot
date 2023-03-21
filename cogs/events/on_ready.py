from discord.ext import commands


class OnReady(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot created by Ben Wager.")
        invite_link = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=2048&scope=bot"
        print(f"Invite link: {invite_link}")


async def setup(bot):
    await bot.add_cog(OnReady(bot))

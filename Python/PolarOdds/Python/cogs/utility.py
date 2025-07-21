import discord
from discord import app_commands
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="h", description="Shows the help menu")
    async def help(self, interaction: discord.Interaction):
        em1 = discord.Embed(title='Terms after ***** are optional.', color=discord.Color.magenta())
        em1.description = (
            "`/h` *Shows Help Menu*\n"
            "`/av * user` *View Avatar*\n"
            "`/c` *Clear Messages (Mod Only)*\n"
            "`/cs` *Clear Snipe (Mod Only)*\n"
            "`/es` *Edit Snipe (Mod Only)*\n"
            "`/rto user` *Remove Timeout (Mod Only)*\n"
            "`/s` *Snipe Message (Mod Only)*\n"
            "`/to user * days/hours/minutes/seconds` *Timeout Member (Mod Only)*"
        )
        em2 = discord.Embed(color=discord.Color.magenta())
        em2.description = f"<:check:1136292889111048304> {interaction.user.mention}: Check your DMS!"
        
        await interaction.user.send(embed=em1)
        await interaction.response.send_message(embed=em2)

    @app_commands.command(name="av", description="See a user's avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        if user is None:
            user = interaction.user
            
        em = discord.Embed(color=discord.Color.magenta())
        em.set_image(url=user.avatar.url)
        em.description = f"[**{user}'s avatar**]({user.avatar.url})"
        
        if user != interaction.user:
            em.set_author(name=str(interaction.user), icon_url=interaction.user.avatar.url)
            
        await interaction.response.send_message(embed=em)

async def setup(bot):
    await bot.add_cog(Utility(bot)) 
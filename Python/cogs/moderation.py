import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sniped_message = None
        self.sniped_author = None
        self.edited_old = None
        self.edited_new = None
        self.edited_author = None

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        self.sniped_message = message.content
        self.sniped_author = str(message.author)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        self.edited_old = before.content
        self.edited_new = after.content
        self.edited_author = after.author

    @app_commands.command(name="s", description="View the most recently deleted message in this channel.")
    async def snipe(self, interaction: discord.Interaction):
        if self.sniped_message is None:
            nomsg = discord.Embed(color=discord.Color.light_grey())
            nomsg.description = f"<:xmark:1136292933268672522> {interaction.user.mention}: Snipe failed; no recently **deleted messages**"
            await interaction.response.send_message(embed=nomsg, ephemeral=False)
        else:
            msg = discord.Embed(color=discord.Color.magenta())
            msg.description = self.sniped_message
            msg.set_author(name=self.sniped_author)
            await interaction.response.send_message(embed=msg, ephemeral=False)

    @app_commands.command(name="cs", description="Clear recently deleted message history.")
    async def clear_snipe(self, interaction: discord.Interaction):
        if self.sniped_message is None:
            none = discord.Embed(color=discord.Color.light_grey())
            none.description = f"<:xmark:1136292933268672522> {interaction.user.mention}: There are no **recently deleted** messages to **clear**"
            await interaction.response.send_message(embed=none)
        else:
            self.sniped_message = None
            self.sniped_author = None
            cem = discord.Embed(color=discord.Color.magenta())
            cem.description = f"<:check:1136292889111048304> {interaction.user.mention}: Previously **deleted messages** were **cleared**"
            await interaction.response.send_message(embed=cem, ephemeral=False)

    @app_commands.command(name="es", description="View the most recently edited message")
    async def edit_snipe(self, interaction: discord.Interaction):
        if self.edited_new is None:
            nonew = discord.Embed(color=discord.Color.light_grey())
            nonew.description = f"<:xmark:1136292933268672522> {interaction.user.mention}: There are no recently **edited messages**"
            await interaction.response.send_message(embed=nonew)
        else:
            yesnew = discord.Embed(color=discord.Color.magenta())
            yesnew.description = f"Original: *{self.edited_old}*\n> New: *{self.edited_new}*"
            yesnew.set_author(name=self.edited_author)
            await interaction.response.send_message(embed=yesnew)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        adminrole = message.guild.get_role(133586119356285124)
        timeoutrole = message.guild.get_role(1338586765342019604)
        
        not_allowed = ['discord.gg', 'https://']
        for notallowed in not_allowed:
            if notallowed in message.content:
                if adminrole in message.author.roles:
                    return
                    
                await message.delete()
                await message.author.add_roles(timeoutrole)
                
                em = discord.Embed(color=discord.Color.light_grey())
                em.description = f"⚠️ {message.author.mention}: **Links** are not allowed in this server. You have been put in <#1338941852052754453>"
                
                await message.author.send(embed=em)
                await message.channel.send(embed=em)
                
                duration = timedelta(seconds=59, minutes=59, hours=23, days=13)
                await message.author.timeout(duration, reason=f"{message.author} timed out by PolarOdds: AutoMod (Link Blocking).")

async def setup(bot):
    await bot.add_cog(Moderation(bot)) 
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
from datetime import datetime
import pytz
from config import TOKEN

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='-', intents=intents)

bot.remove_command("help")

ownerid = 825106419333857312
botid = 1338579705628201061
guildid = 1338581149374480496

commands_synced = False

@bot.event
async def on_ready():
    global commands_synced
    if not commands_synced:
        print("Syncing commands...")
        try:
            await bot.tree.sync()
            print("Commands synced successfully!")
            commands_synced = True
        except Exception as e:
            print(f"Failed to sync commands: {e}")
    
    print(f"{bot.user} is ready!")

@bot.tree.command(name="sync", description="Owner only - Sync commands")
async def sync(interaction: discord.Interaction):
    if interaction.user.id != ownerid:
        await interaction.response.send_message("Only the bot owner can use this command!", ephemeral=True)
        return
        
    print("Manual sync requested...")
    try:
        await bot.tree.sync()
        await interaction.response.send_message("Commands synced globally!", ephemeral=True)
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        await interaction.response.send_message(f"Failed to sync commands: {e}", ephemeral=True)

def get_cog_choices():
    choices = []
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = filename[:-3]
            choices.append(app_commands.Choice(name=cog_name, value=cog_name))
    return choices

@bot.tree.command(name="reload", description="Owner only - Reload cogs")
@app_commands.choices(cog=[
    app_commands.Choice(name="all", value="all"),
    *get_cog_choices()
])
async def reload(interaction: discord.Interaction, cog: app_commands.Choice[str]):
    if interaction.user.id != ownerid:
        await interaction.response.send_message("Only the bot owner can use this command!", ephemeral=True)
        return

    elif cog.value == "all":
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await bot.reload_extension(f"cogs.{filename[:-3]}")
                    print(f"Reloaded extension: {filename[:-3]}")
                except Exception as e:
                    print(f"Failed to reload extension {filename}: {e}")
        await interaction.response.send_message("All cogs reloaded!", ephemeral=True)
        await bot.tree.sync()
    else:
        try:
            await bot.reload_extension(f"cogs.{cog.value}")
            print(f"Reloaded extension: {cog.value}")
            await interaction.response.send_message(f"Reloaded cog: {cog.value}", ephemeral=True)
            guild = discord.Object(id=1338581149374480496)
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"Failed to reload extension {cog.value}: {e}")
            await interaction.response.send_message(f"Failed to reload cog {cog.value}: {e}", ephemeral=True)
       
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded extension: {filename[:-3]}")
            except Exception as e:
                print(f"Failed to load extension {filename}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
import discord
from discord import app_commands
from discord.ext import commands

class ReactionRoles(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.select(
        custom_id="role_selection",
        placeholder="Select your roles",
        min_values=0,
        max_values=3,
        options=[
            discord.SelectOption(
                label="Parlay Tracker",
                value="parlay_tracker",
                description="Track parlays and get picks",
                default=False
            ),
            discord.SelectOption(
                label="Discussions",
                value="discussions",
                description="Discuss picks with others",
                default=False
            ),
            discord.SelectOption(
                label="Pick Pings",
                value="pick_pings",
                description="Get notified of new picks",
                default=False
            )
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        member = interaction.user
        
        # Get role objects
        ptrackerrole = interaction.guild.get_role(1338599658439839917)
        discussionrole = interaction.guild.get_role(1338599617444581488)
        pickpingsrole = interaction.guild.get_role(1338599707756462141)
        
        # Create a mapping of values to roles
        role_mapping = {
            "parlay_tracker": ptrackerrole,
            "discussions": discussionrole,
            "pick_pings": pickpingsrole
        }
        
        # Update roles based on selection
        changes = []
        for value, role in role_mapping.items():
            has_role = role in member.roles
            should_have_role = value in select.values
            
            if should_have_role and not has_role:
                await member.add_roles(role)
                changes.append(f"Added: {role.name}")
            elif not should_have_role and has_role:
                await member.remove_roles(role)
                changes.append(f"Removed: {role.name}")
        
        if changes:
            await interaction.response.send_message("\n".join(changes), ephemeral=True)
        else:
            await interaction.response.send_message("No changes made to your roles", ephemeral=True)

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roles", description=". . .")
    async def roles(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(1338603689950056518)
        em = discord.Embed(title="Server Roles", color=0xd6e1ff)
        em.description = (
            f"<@&1338599658439839917> Choose this role to track parlays and get picks.\n"
            f"<@&1338599617444581488> Choose this role to discuss your/other's picks.\n"
            f"<@&1338599707756462141> Choose this role to receive pings when good picks are available."
        )
        em.set_image(url="https://imagizer.imageshack.com/img922/1084/yQ9X2K.png")
        await channel.send(embed=em, view=ReactionRoles())

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ReactionRoles())

async def setup(bot):
    await bot.add_cog(Roles(bot)) 
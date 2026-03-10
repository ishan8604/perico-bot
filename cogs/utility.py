import discord
from discord.ext import commands
from discord import app_commands

# --- 1. The Dropdown Logic ---
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moderation", description="Kick, Ban, Timeout, Purge, Userinfo", emoji="🛡️"),
            discord.SelectOption(label="Admin Setup", description="Config Welcome, Leave, Logs, Stats", emoji="⚙️"),
            discord.SelectOption(label="Community", description="Giveaways, Polls, Suggestions", emoji="🎉"),
            discord.SelectOption(label="Engagement", description="Rank, Leaderboard, Self-Roles", emoji="📈"),
            discord.SelectOption(label="Tickets", description="Setup and Manage Support Tickets", emoji="🎫")
        ]
        super().__init__(placeholder="Choose a category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Moderation":
            embed = discord.Embed(title="🛡️ Moderation Commands", color=discord.Color.red())
            embed.add_field(name="/kick", value="`Usage: /kick [member] [reason]` - Removes a member from the server.", inline=False)
            embed.add_field(name="/ban", value="`Usage: /ban [member] [reason]` - Permanently bans a member.", inline=False)
            embed.add_field(name="/timeout", value="`Usage: /timeout [member] [minutes] [reason]` - Mutes a member temporarily.", inline=False)
            embed.add_field(name="/purge", value="`Usage: /purge [amount]` - Deletes a specific number of messages.", inline=False)
            embed.add_field(name="/userinfo", value="`Usage: /userinfo [member]` - Shows deep-dive data on a user.", inline=False)
            embed.add_field(name="/warn /warnings", value="`Usage: /warn [member] [reason]` - Manage user infractions.", inline=False)

        elif self.values[0] == "Admin Setup":
            embed = discord.Embed(title="⚙️ Admin Setup Commands", color=discord.Color.blue())
            embed.add_field(name="/set_welcome", value="Set the welcome channel and auto-role.", inline=False)
            embed.add_field(name="/set_leave", value="Set the goodbye channel and custom message.", inline=False)
            embed.add_field(name="/set_logging", value="Set the channel for message & command logs.", inline=False)
            embed.add_field(name="/set_suggestions", value="Setup the suggestion channel and ping role.", inline=False)
            embed.add_field(name="/add_banned_word", value="Add words to the Auto-Mod filter.", inline=False)
            embed.add_field(name="/toggle_invites", value="Enable/Disable anti-invite link protection.", inline=False)

        elif self.values[0] == "Community":
            embed = discord.Embed(title="🎉 Community Commands", color=discord.Color.gold())
            embed.add_field(name="/giveaway", value="`Usage: /giveaway [time] [winners] [prize]` - Start a giveaway.", inline=False)
            embed.add_field(name="/poll", value="`Usage: /poll [question] [options]` - Create a multi-choice poll.", inline=False)
            embed.add_field(name="/suggest", value="`Usage: /suggest [idea]` - Submit a suggestion for voting.", inline=False)

        elif self.values[0] == "Engagement":
            embed = discord.Embed(title="📈 Engagement Commands", color=discord.Color.green())
            embed.add_field(name="/rank", value="Check your current level and XP progress.", inline=False)
            embed.add_field(name="/leaderboard", value="See the top 10 most active members.", inline=False)
            embed.add_field(name="/add_role", value="Add a role to the self-assign menu.", inline=False)
            embed.add_field(name="/setup_roles", value="Post the dropdown role selection menu.", inline=False)

        elif self.values[0] == "Tickets":
            embed = discord.Embed(title="🎫 Ticket Commands", color=discord.Color.teal())
            embed.add_field(name="/set_support_role", value="Define which role can see and claim tickets.", inline=False)
            embed.add_field(name="/setup_tickets", value="Create the 'Open Ticket' button panel.", inline=False)
            embed.add_field(name="/add_member", value="Add a user to an existing ticket channel.", inline=False)

        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(HelpDropdown())

# --- 2. The Cog ---
class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`")

    @app_commands.command(name="help", description="View all available commands and how to use them.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Bot Command Center", 
            description="Please select a category from the dropdown menu below to view specific commands and their usage.",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, view=HelpView())

    @app_commands.command(name="userinfo", description="Get detailed information about a member.")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        roles = [role.mention for role in member.roles[1:]]
        embed = discord.Embed(title=f"User Info - {member}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="Joined Discord", value=member.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if roles else "None", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Get detailed information about this server.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.blue())
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Members", value=f"{guild.member_count}", inline=True)
        embed.add_field(name="Boosts", value=f"Level {guild.premium_tier}", inline=True)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
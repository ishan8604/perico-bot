import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kicks a user.")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        await member.kick(reason=reason)
        embed = discord.Embed(title="🔨 Kicked", description=f"{member.mention} was kicked for: {reason}", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Bans a user.")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        await member.ban(reason=reason)
        embed = discord.Embed(title="🚫 Banned", description=f"{member.mention} was banned for: {reason}", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Mutes a user.")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        embed = discord.Embed(title="⏱️ Timed Out", description=f"{member.mention} timed out for {minutes}m. Reason: {reason}", color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="purge", description="Deletes messages.")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True) 
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
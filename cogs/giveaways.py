import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import datetime
import io

# Helper to convert time strings (10m, 1h, 1d) to seconds
def parse_time(time_str):
    time_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    unit = time_str[-1].lower()
    if unit not in time_dict: return -1
    try:
        val = int(time_str[:-1])
    except ValueError:
        return -2
    return val * time_dict[unit]

# --- 1. The Interactive Button View ---
class GiveawayView(discord.ui.View):
    def __init__(self, prize, winners, end_time, host_mention):
        super().__init__(timeout=None) # Persistent
        self.entries = []
        self.prize = prize
        self.winners = winners
        self.end_time = end_time
        self.host_mention = host_mention

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.success, emoji="🎉", custom_id="enter_giveaway_btn")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entries:
            await interaction.response.send_message("❌ You have already entered this giveaway!", ephemeral=True)
            return
        
        # Add user to list
        self.entries.append(interaction.user.id)
        
        # Create the updated embed with the new entry count
        timestamp = f"<t:{int(self.end_time.timestamp())}:R>"
        embed = discord.Embed(
            title="🎉 GIVEAWAY STARTED 🎉",
            description=f"**Prize:** {self.prize}\n**Ends:** {timestamp}\n**Winners:** {self.winners}\n**Hosted by:** {self.host_mention}\n\n**Total Entries:** `{len(self.entries)}`",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Click the button below to join!")

        # Update the original message to show the new count
        await interaction.response.edit_message(embed=embed, view=self)

# --- 2. The Giveaways Cog ---
class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Note: Because this View requires arguments in __init__, 
        # persistent restarts for active giveaways would require a database.
        # For now, this handles active sessions perfectly.
        pass

    @app_commands.command(name="giveaway", description="Start a high-stakes giveaway with a live entry counter.")
    @app_commands.describe(duration="e.g. 10m, 1h, 1d", winners="Number of winners", prize="The prize name", ping_role="Optional role to tag")
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway(self, interaction: discord.Interaction, duration: str, winners: int, prize: str, ping_role: discord.Role = None):
        seconds = parse_time(duration)
        if seconds < 0:
            await interaction.response.send_message("❌ Invalid time! Use `10m`, `1h`, or `1d`.", ephemeral=True)
            return

        # Calculate timing
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        timestamp = f"<t:{int(end_time.timestamp())}:R>"

        # Build the initial embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY STARTED 🎉",
            description=f"**Prize:** {prize}\n**Ends:** {timestamp}\n**Winners:** {winners}\n**Hosted by:** {interaction.user.mention}\n\n**Total Entries:** `0`",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Click the button below to join!")

        view = GiveawayView(prize, winners, end_time, interaction.user.mention)
        ping_content = ping_role.mention if ping_role else None
        
        # Send the giveaway message
        await interaction.response.send_message("Giveaway is live!", ephemeral=True)
        giveaway_msg = await interaction.channel.send(content=ping_content, embed=embed, view=view)

        # Wait for the giveaway to finish
        await asyncio.sleep(seconds)

        # --- End of Giveaway Logic ---
        if not view.entries:
            error_embed = discord.Embed(title="⚠️ Giveaway Ended", description=f"The giveaway for **{prize}** has ended, but nobody entered!", color=discord.Color.red())
            await giveaway_msg.edit(embed=error_embed, view=None)
            return

        # Determine winners (handle case where entries < requested winners)
        actual_winner_count = min(len(view.entries), winners)
        winner_ids = random.sample(view.entries, actual_winner_count)
        winner_mentions = ", ".join([f"<@{uid}>" for uid in winner_ids])

        # Finalize the embed
        end_embed = discord.Embed(
            title="🎊 GIVEAWAY ENDED 🎊",
            description=f"**Prize:** {prize}\n**Winners:** {winner_mentions}\n**Total Entries:** `{len(view.entries)}`",
            color=discord.Color.gold()
        )
        end_embed.set_footer(text="Congratulations to the winners!")

        await giveaway_msg.edit(embed=end_embed, view=None)
        await interaction.channel.send(f"Congratulations {winner_mentions}! You won the **{prize}**!")

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
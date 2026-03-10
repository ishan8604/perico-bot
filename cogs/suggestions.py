import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('suggestions.db')
        self.cursor = self.conn.cursor()
        
        # 1. Create the base table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        ''')
        
        # 2. Safe Database Upgrade: Add the role column if it doesn't exist yet
        try:
            self.cursor.execute('ALTER TABLE config ADD COLUMN ping_role_id INTEGER')
        except sqlite3.OperationalError:
            pass # The column already exists, we are good to go!
            
        self.conn.commit()

    # --- Admin Setup Command ---

    @app_commands.command(name="set_suggestions", description="Set the channel and optional ping role for suggestions.")
    @app_commands.default_permissions(administrator=True)
    async def set_suggestions(self, interaction: discord.Interaction, channel: discord.TextChannel, ping_role: discord.Role = None):
        # Save both the channel and the role (if provided) to the database
        role_id = ping_role.id if ping_role else None
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO config (guild_id, channel_id, ping_role_id) 
            VALUES (?, ?, ?)
        ''', (interaction.guild.id, channel.id, role_id))
        self.conn.commit()
        
        # Format a nice confirmation message
        msg = f"✅ Suggestions will now be posted in {channel.mention}."
        if ping_role:
            msg += f"\n🔔 I will also ping {ping_role.mention} for new suggestions."
            
        await interaction.response.send_message(msg, ephemeral=True)

    # --- User Suggest Command ---

    @app_commands.command(name="suggest", description="Submit an idea or suggestion for the server.")
    async def suggest(self, interaction: discord.Interaction, idea: str):
        await interaction.response.defer(ephemeral=True)

        # 1. Fetch settings from database
        self.cursor.execute('SELECT channel_id, ping_role_id FROM config WHERE guild_id = ?', (interaction.guild.id,))
        result = self.cursor.fetchone()

        if not result:
            await interaction.followup.send("❌ The suggestion system hasn't been set up. Ask an admin to run `/set_suggestions`.", ephemeral=True)
            return

        channel_id, ping_role_id = result
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel:
            await interaction.followup.send("❌ The suggestion channel is invalid. An admin needs to reset it.", ephemeral=True)
            return

        # 2. Create the embed
        embed = discord.Embed(
            title="💡 New Suggestion", 
            description=idea, 
            color=discord.Color.gold()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        # 3. Figure out if we need to ping a role
        ping_content = None
        if ping_role_id:
            role = interaction.guild.get_role(ping_role_id)
            if role:
                ping_content = role.mention # Put the ping in the message content!

        # 4. Send the message
        try:
            # We send the ping_content text AND the embed together
            suggestion_msg = await channel.send(content=ping_content, embed=embed)
            
            await suggestion_msg.add_reaction("👍")
            await suggestion_msg.add_reaction("👎")
            
            await interaction.followup.send(f"✅ Your suggestion has been successfully submitted to {channel.mention}!", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to send messages or add reactions in the suggestion channel.", ephemeral=True)

# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(Suggestions(bot))
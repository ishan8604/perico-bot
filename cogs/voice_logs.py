import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class VoiceLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('server_settings.db')
        self.cursor = self.conn.cursor()
        
        # Ensure the column for voice logs exists
        try:
            self.cursor.execute('ALTER TABLE settings ADD COLUMN voice_log_channel_id INTEGER')
        except sqlite3.OperationalError:
            pass # Column already exists
        self.conn.commit()

    def get_voice_log_channel(self, guild_id):
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT voice_log_channel_id FROM settings WHERE guild_id = ?', (guild_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else None

    # --- Command to Set the Channel ---
    @app_commands.command(name="set_voice_logs", description="Set the channel where voice join/leave logs are sent.")
    @app_commands.describe(channel="The channel to send voice logs to")
    @app_commands.default_permissions(administrator=True)
    async def set_voice_logs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Ensure guild entry exists
        self.cursor.execute('INSERT OR IGNORE INTO settings (guild_id) VALUES (?)', (interaction.guild.id,))
        
        self.cursor.execute('UPDATE settings SET voice_log_channel_id = ? WHERE guild_id = ?', (channel.id, interaction.guild.id))
        self.conn.commit()
        
        await interaction.response.send_message(f"✅ Voice logs will now be sent to {channel.mention}", ephemeral=True)

    # --- The Event Listener ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

        channel_id = self.get_voice_log_channel(member.guild.id)
        if not channel_id: return
        
        log_channel = self.bot.get_channel(channel_id)
        if not log_channel: return

        embed = discord.Embed(timestamp=discord.utils.utcnow())
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)

        # Logic for Join/Leave/Move
        if before.channel is None and after.channel is not None:
            embed.title = "🔈 User Joined VC"
            embed.description = f"{member.mention} joined **{after.channel.name}**"
            embed.color = discord.Color.green()
        
        elif before.channel is not None and after.channel is None:
            embed.title = "🔇 User Left VC"
            embed.description = f"{member.mention} left **{before.channel.name}**"
            embed.color = discord.Color.red()
            
        elif before.channel and after.channel and before.channel.id != after.channel.id:
            embed.title = "🔄 User Switched VC"
            embed.description = f"{member.mention} moved: **{before.channel.name}** ➡️ **{after.channel.name}**"
            embed.color = discord.Color.blue()
        else:
            return # Ignore mutes/deafens to keep logs clean

        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceLogs(bot))
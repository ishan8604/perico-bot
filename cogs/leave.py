import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Leave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('server_settings.db')
        self.cursor = self.conn.cursor()
        
        # Ensure the columns exist for leave settings
        try:
            self.cursor.execute('ALTER TABLE settings ADD COLUMN leave_channel_id INTEGER')
            self.cursor.execute('ALTER TABLE settings ADD COLUMN leave_message TEXT')
        except sqlite3.OperationalError:
            pass # Columns already exist
        self.conn.commit()

    def get_settings(self, guild_id):
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT leave_channel_id, leave_message FROM settings WHERE guild_id = ?', (guild_id,))
        res = cursor.fetchone()
        conn.close()
        return res

    # --- Admin Configuration Command ---

    @app_commands.command(name="set_leave", description="Set the channel and message for when members leave.")
    @app_commands.describe(channel="Where to send the message", message="Use {user} to mention the person")
    @app_commands.default_permissions(administrator=True)
    async def set_leave(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str = None):
        # Ensure guild exists in settings
        self.cursor.execute('INSERT OR IGNORE INTO settings (guild_id) VALUES (?)', (interaction.guild.id,))
        
        self.cursor.execute('''
            UPDATE settings 
            SET leave_channel_id = ?, leave_message = ? 
            WHERE guild_id = ?
        ''', (channel.id, message, interaction.guild.id))
        self.conn.commit()
        
        await interaction.response.send_message(f"✅ Leave messages will be sent to {channel.mention}.", ephemeral=True)

    # --- The Leave Listener ---

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = self.get_settings(member.guild.id)
        if not settings:
            return
            
        leave_channel_id, custom_message = settings

        if leave_channel_id:
            channel = self.bot.get_channel(leave_channel_id)
            if channel:
                # 1. Determine the message content
                if custom_message:
                    # Replace {user} with the member's name safely
                    description = custom_message.replace("{user}", member.display_name)
                else:
                    # Default "Sad" Message
                    description = f"Goodbye **{member.display_name}**... we are sad to see you leave. 😢"

                # 2. Create the Embed
                embed = discord.Embed(
                    title="Member Left",
                    description=description,
                    color=discord.Color.red()
                )
                if member.avatar:
                    embed.set_thumbnail(url=member.avatar.url)
                embed.set_footer(text=f"We now have {member.guild.member_count} members.")
                
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leave(bot))
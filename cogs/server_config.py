import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class ServerConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('server_settings.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                default_role_id INTEGER,
                log_channel_id INTEGER,
                support_role_id INTEGER
            )
        ''')
        self.conn.commit()

    def ensure_guild(self, guild_id):
        self.cursor.execute('INSERT OR IGNORE INTO settings (guild_id) VALUES (?)', (guild_id,))
        self.conn.commit()

    @app_commands.command(name="set_welcome", description="Set the welcome channel and default role.")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role = None):
        self.ensure_guild(interaction.guild.id)
        role_id = role.id if role else None
        
        self.cursor.execute('UPDATE settings SET welcome_channel_id = ?, default_role_id = ? WHERE guild_id = ?', 
                           (channel.id, role_id, interaction.guild.id))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="set_logging", description="Set the channel for deleted/edited message logs.")
    @app_commands.default_permissions(administrator=True)
    async def set_logging(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.ensure_guild(interaction.guild.id)
        self.cursor.execute('UPDATE settings SET log_channel_id = ? WHERE guild_id = ?', (channel.id, interaction.guild.id))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Log channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="set_support_role", description="Set the role that can view and claim tickets.")
    @app_commands.default_permissions(administrator=True)
    async def set_support_role(self, interaction: discord.Interaction, role: discord.Role):
        self.ensure_guild(interaction.guild.id)
        self.cursor.execute('UPDATE settings SET support_role_id = ? WHERE guild_id = ?', (role.id, interaction.guild.id))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Support role set to {role.mention}.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerConfig(bot))
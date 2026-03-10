import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('warnings.db')
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                warning_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                mod_id INTEGER,
                reason TEXT,
                date TEXT
            )
        ''')
        self.conn.commit()

    @app_commands.command(name="warn", description="Warns a user.")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('INSERT INTO warnings (user_id, guild_id, mod_id, reason, date) VALUES (?, ?, ?, ?, ?)', 
                           (member.id, interaction.guild.id, interaction.user.id, reason, date))
        self.conn.commit()
        
        embed = discord.Embed(title="⚠️ Warned", description=f"{member.mention} was warned for: {reason}", color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warnings", description="Check warning history.")
    @app_commands.default_permissions(moderate_members=True)
    async def check_warnings(self, interaction: discord.Interaction, member: discord.Member):
        self.cursor.execute('SELECT warning_id, mod_id, reason, date FROM warnings WHERE user_id = ? AND guild_id = ?', 
                           (member.id, interaction.guild.id))
        records = self.cursor.fetchall()
        
        if not records:
            await interaction.response.send_message("✅ Clean record.", ephemeral=True)
            return
            
        embed = discord.Embed(title=f"Warnings for {member.display_name}", description=f"Total: {len(records)}", color=discord.Color.orange())
        for row in records[-25:]:
            embed.add_field(name=f"ID: {row[0]} | {row[3]}", value=f"**Mod:** <@{row[1]}>\n**Reason:** {row[2]}", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delwarn", description="Delete a warning by ID.")
    @app_commands.default_permissions(administrator=True)
    async def delwarn(self, interaction: discord.Interaction, warning_id: int):
        self.cursor.execute('DELETE FROM warnings WHERE warning_id = ? AND guild_id = ?', (warning_id, interaction.guild.id))
        self.conn.commit()
        await interaction.response.send_message(f"🗑️ Deleted warning `#{warning_id}`.")

async def setup(bot):
    await bot.add_cog(Warnings(bot))
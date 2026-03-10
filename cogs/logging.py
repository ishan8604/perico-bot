import discord
from discord.ext import commands
import sqlite3

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_log_channel(self, guild_id):
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT log_channel_id FROM settings WHERE guild_id = ?', (guild_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else None

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.content: return
        
        log_id = self.get_log_channel(message.guild.id)
        if not log_id: return
        
        channel = self.bot.get_channel(log_id)
        if channel:
            embed = discord.Embed(title="🗑️ Message Deleted", description=f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n\n{message.content}", color=discord.Color.red())
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content: return
            
        log_id = self.get_log_channel(before.guild.id)
        if not log_id: return
        
        channel = self.bot.get_channel(log_id)
        if channel:
            embed = discord.Embed(title="✏️ Message Edited", description=f"**Channel:** {before.channel.mention} [Jump]({after.jump_url})", color=discord.Color.orange())
            embed.add_field(name="Before", value=before.content or "*Empty*", inline=False)
            embed.add_field(name="After", value=after.content or "*Empty*", inline=False)
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
import discord
from discord.ext import commands
import sqlite3

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_settings(self, guild_id):
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT welcome_channel_id, default_role_id FROM settings WHERE guild_id = ?', (guild_id,))
        res = cursor.fetchone()
        conn.close()
        return res

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        settings = self.get_settings(member.guild.id)
        if not settings: 
            return
            
        welcome_id, role_id = settings

        if welcome_id:
            channel = self.bot.get_channel(welcome_id)
            if channel:
                embed = discord.Embed(
                    title=f"Welcome to {member.guild.name}!",
                    description=f"Hello {member.mention}, we are glad you're here!",
                    color=discord.Color.purple()
                )
                if member.avatar: 
                    embed.set_thumbnail(url=member.avatar.url)
                embed.set_footer(text=f"Member #{member.guild.member_count}")
                await channel.send(embed=embed)

        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try: 
                    await member.add_roles(role)
                except discord.Forbidden: 
                    pass

async def setup(bot):
    await bot.add_cog(Welcome(bot))
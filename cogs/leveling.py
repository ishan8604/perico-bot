import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import math

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('leveling.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        self.conn.commit()
        
        # Cooldown dictionary to prevent XP spamming {user_id: guild_id}
        self.cooldowns = {}

    # Helper to calculate XP needed for a specific level
    def get_xp_for_level(self, level):
        # Formula: 100 * (level ^ 2) + 100
        return 100 * (level ** 2) + 100

    # Helper to get or create a level role with a specific color
    async def get_or_create_role(self, guild, level):
        role_name = f"Level {level}"
        role = discord.utils.get(guild.roles, name=role_name)
        
        if not role:
            # Different colors for different levels
            colors = [
                discord.Color.light_gray(), # Lvl 1
                discord.Color.blue(),       # Lvl 2
                discord.Color.teal(),       # Lvl 3
                discord.Color.green(),      # Lvl 4
                discord.Color.gold(),       # Lvl 5
                discord.Color.orange(),     # Lvl 6
                discord.Color.magenta(),    # Lvl 7
                discord.Color.purple(),     # Lvl 8
                discord.Color.red(),        # Lvl 9
                discord.Color.dark_red()    # Lvl 10
            ]
            color = colors[min(level-1, 9)]
            role = await guild.create_role(name=role_name, color=color, reason="Auto Leveling Role")
        return role

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # XP Cooldown: Users only get XP once every 30 seconds
        user_key = (message.author.id, message.guild.id)
        if user_key in self.cooldowns:
            return

        # 1. Fetch User Data
        self.cursor.execute('INSERT OR IGNORE INTO users (guild_id, user_id) VALUES (?, ?)', (message.guild.id, message.author.id))
        self.cursor.execute('SELECT xp, level FROM users WHERE guild_id = ? AND user_id = ?', (message.guild.id, message.author.id))
        xp, level = self.cursor.fetchone()

        # 2. Add Random XP (15 to 25)
        new_xp = xp + random.randint(15, 25)
        xp_needed = self.get_xp_for_level(level + 1)

        # 3. Check for Level Up (Max level 10)
        if new_xp >= xp_needed and level < 10:
            level += 1
            new_xp = 0 # Reset XP for the new level
            
            # Update Database
            self.cursor.execute('UPDATE users SET xp = ?, level = ? WHERE guild_id = ? AND user_id = ?', (new_xp, level, message.guild.id, message.author.id))
            self.conn.commit()

            # Assign Role
            role = await self.get_or_create_role(message.guild, level)
            try:
                await message.author.add_roles(role)
                
                # Send Level Up Embed
                embed = discord.Embed(
                    title="🆙 LEVEL UP!",
                    description=f"Congratulations {message.author.mention}!\nYou just reached **Level {level}**!",
                    color=role.color
                )
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Missing permissions to add role in {message.guild.name}")
        else:
            # Just update XP
            self.cursor.execute('UPDATE users SET xp = ? WHERE guild_id = ? AND user_id = ?', (new_xp, message.guild.id, message.author.id))
            self.conn.commit()

        # Add to cooldown and remove after 30 seconds
        self.cooldowns[user_key] = True
        import asyncio
        await asyncio.sleep(30)
        del self.cooldowns[user_key]

    @app_commands.command(name="rank", description="Check your current level and XP progress.")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        self.cursor.execute('SELECT xp, level FROM users WHERE guild_id = ? AND user_id = ?', (interaction.guild.id, member.id))
        result = self.cursor.fetchone()

        if not result:
            await interaction.response.send_message(f"{member.display_name} hasn't started chatting yet!", ephemeral=True)
            return

        xp, level = result
        xp_needed = self.get_xp_for_level(level + 1)
        
        embed = discord.Embed(title=f"📊 {member.display_name}'s Rank", color=discord.Color.blue())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp} / {xp_needed}**", inline=True)
        
        # Simple progress bar
        percentage = min(int((xp / xp_needed) * 10), 10)
        progress_bar = "🟦" * percentage + "⬜" * (10 - percentage)
        embed.add_field(name="Progress", value=progress_bar, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Show the top 10 most active members.")
    async def leaderboard(self, interaction: discord.Interaction):
        self.cursor.execute('SELECT user_id, level, xp FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10', (interaction.guild.id,))
        top_users = self.cursor.fetchall()

        if not top_users:
            await interaction.response.send_message("The leaderboard is empty!", ephemeral=True)
            return

        embed = discord.Embed(title=f"🏆 {interaction.guild.name} Leaderboard", color=discord.Color.gold())
        
        description = ""
        for i, (user_id, level, xp) in enumerate(top_users, 1):
            user = self.bot.get_user(user_id) or f"User({user_id})"
            description += f"**{i}.** {user} - Lvl {level} ({xp} XP)\n"
        
        embed.description = description
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
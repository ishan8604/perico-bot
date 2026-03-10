import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import re
import asyncio

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to a new database for automod settings
        self.conn = sqlite3.connect('automod.db')
        self.cursor = self.conn.cursor()
        
        # Table 1: Banned words per server
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_words (
                guild_id INTEGER,
                word TEXT,
                PRIMARY KEY (guild_id, word)
            )
        ''')
        
        # Table 2: Settings (e.g., is anti-invite enabled?)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                anti_invite INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    # --- 1. Admin Commands ---

    @app_commands.command(name="add_banned_word", description="Add a word to the Auto-Mod filter.")
    @app_commands.default_permissions(manage_messages=True)
    async def add_word(self, interaction: discord.Interaction, word: str):
        word = word.lower().strip()
        self.cursor.execute('INSERT OR IGNORE INTO banned_words (guild_id, word) VALUES (?, ?)', (interaction.guild.id, word))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Added `{word}` to the banned words list.", ephemeral=True)

    @app_commands.command(name="remove_banned_word", description="Remove a word from the Auto-Mod filter.")
    @app_commands.default_permissions(manage_messages=True)
    async def remove_word(self, interaction: discord.Interaction, word: str):
        self.cursor.execute('DELETE FROM banned_words WHERE guild_id = ? AND word = ?', (interaction.guild.id, word.lower()))
        self.conn.commit()
        await interaction.response.send_message(f"🗑️ Removed `{word}` from the banned words list.", ephemeral=True)

    @app_commands.command(name="toggle_invites", description="Enable or disable the anti-invite filter.")
    @app_commands.default_permissions(manage_messages=True)
    async def toggle_invites(self, interaction: discord.Interaction, enabled: bool):
        status = 1 if enabled else 0
        self.cursor.execute('INSERT OR REPLACE INTO settings (guild_id, anti_invite) VALUES (?, ?)', (interaction.guild.id, status))
        self.conn.commit()
        state = "enabled" if enabled else "disabled"
        await interaction.response.send_message(f"✅ Anti-invite filter has been **{state}**.", ephemeral=True)

    # --- 2. The Background Listener ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and users with 'Manage Messages' permission (admins/mods)
        if message.author.bot or message.author.guild_permissions.manage_messages:
            return

        content = message.content.lower()

        # Check for Banned Words
        self.cursor.execute('SELECT word FROM banned_words WHERE guild_id = ?', (message.guild.id,))
        banned_words = [row[0] for row in self.cursor.fetchall()]
        
        for word in banned_words:
            if word in content:
                await self.punish(message, f"Contains banned word: `{word}`")
                return

        # Check for Discord Invites (RegEx)
        self.cursor.execute('SELECT anti_invite FROM settings WHERE guild_id = ?', (message.guild.id,))
        res = self.cursor.fetchone()
        if res and res[0] == 1:
            # Match common discord invite patterns
            invite_pattern = r"(discord\.gg\/|discord\.com\/invite\/)[a-z0-9]+"
            if re.search(invite_pattern, content):
                await self.punish(message, "Sent an unauthorized Discord invite link.")
                return

    async def punish(self, message, reason):
        try:
            await message.delete()
            # Send a warning to the channel that deletes itself after 5 seconds
            warn_msg = await message.channel.send(f"⚠️ {message.author.mention}, your message was removed. Reason: {reason}")
            await asyncio.sleep(5)
            await warn_msg.delete()
        except discord.Forbidden:
            print(f"Failed to delete message in {message.guild.name} - Missing Permissions.")

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
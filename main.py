import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import sqlite3
import datetime
from dotenv import load_dotenv

load_dotenv()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Anti-Spam Dictionary
        self.spam_control = {}

    async def setup_hook(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded Cog: {filename}")
        
        await self.tree.sync()
        
        # START THE TASKS
        self.update_stats.start()     # Member count voice channel
        self.presence_updater.start()  # NEW: Status updater
        
        print("Bot is fully synced and background tasks started!")

    # --- Feature 1: Member Count Stats ---
    @tasks.loop(minutes=10)
    async def update_stats(self):
        # ... (Keep your existing update_stats code here) ...
        pass

    # --- Feature: Dynamic "Watching" Status ---
    @tasks.loop(minutes=30)
    async def presence_updater(self):
        # Wait until the bot is fully logged in so it can count guilds
        await self.wait_until_ready()
        
        guild_count = len(self.guilds)
        # Create the 'Watching' activity
        activity = discord.Activity(
            type=discord.ActivityType.watching, 
            name=f"Looking after {guild_count} servers"
        )
        
        await self.change_presence(activity=activity)
        print(f"Status updated to: Watching {guild_count} servers")

    @presence_updater.before_loop
    async def before_presence_updater(self):
        await self.wait_until_ready()

bot = MyBot()

# --- Helper: Database Access ---
def get_log_channel_id(guild_id):
    conn = sqlite3.connect('server_settings.db')
    cursor = conn.cursor()
    cursor.execute('SELECT log_channel_id FROM settings WHERE guild_id = ?', (guild_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

# --- Feature 1: Member Count Stats (Runs every 10 mins) ---
@tasks.loop(minutes=10)
async def update_stats():
    for guild in bot.guilds:
        # Look for a voice channel starting with '📊 Total Members:'
        channel = discord.utils.get(guild.voice_channels, name=lambda x: x.startswith("📊 Total Members:"))
        
        # If it doesn't exist, create it (Admin can move it later)
        if not channel:
            try:
                overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False)}
                channel = await guild.create_voice_channel(
                    f"📊 Total Members: {guild.member_count}", 
                    overwrites=overwrites,
                    position=0
                )
            except discord.Forbidden:
                continue
        else:
            # Update the existing channel name
            if channel.name != f"📊 Total Members: {guild.member_count}":
                await channel.edit(name=f"📊 Total Members: {guild.member_count}")

# --- Feature 2: Anti-Spam Listener ---
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Ignore moderators from Anti-Spam
    if message.author.guild_permissions.manage_messages:
        await bot.process_commands(message)
        return

    user_key = (message.author.id, message.guild.id)
    now = datetime.datetime.now()

    if user_key not in bot.spam_control:
        bot.spam_control[user_key] = []

    # Filter out timestamps older than 3 seconds
    bot.spam_control[user_key] = [t for t in bot.spam_control[user_key] if (now - t).total_seconds() < 3]
    bot.spam_control[user_key].append(now)

    # If more than 5 messages in 3 seconds
    if len(bot.spam_control[user_key]) > 5:
        try:
            # Timeout for 10 minutes
            duration = datetime.timedelta(minutes=10)
            await message.author.timeout(duration, reason="Anti-Spam Triggered")
            
            # Delete the spammy messages
            await message.channel.purge(limit=5, check=lambda m: m.author == message.author)
            
            await message.channel.send(f"🚫 {message.author.mention} has been muted for 10 minutes for spamming.", delete_after=10)
        except discord.Forbidden:
            pass

    await bot.process_commands(message)

# --- Feature 3: Command Logging ---
@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    log_id = get_log_channel_id(interaction.guild.id)
    if log_id:
        channel = bot.get_channel(log_id)
        if channel:
            embed = discord.Embed(
                title="📝 Command Log",
                description=f"**User:** {interaction.user.mention}\n**Command:** `/{command.name}`\n**Channel:** {interaction.channel.mention}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            await channel.send(embed=embed)

# --- Feature 4: Global Error Handler ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    embed = discord.Embed(color=discord.Color.red())
    
    if isinstance(error, app_commands.MissingPermissions):
        embed.title = "🚫 Access Denied"
        embed.description = f"You need: `{', '.join(error.missing_permissions)}`"
    elif isinstance(error, app_commands.BotMissingPermissions):
        embed.title = "⚙️ Bot Permission Error"
        embed.description = f"I need: `{', '.join(error.missing_permissions)}`"
    elif isinstance(error, app_commands.CommandOnCooldown):
        embed.title = "⏳ Slow Down"
        embed.description = f"Try again in {error.retry_after:.1f}s."
    else:
        embed.title = "💥 Error"
        embed.description = "An unexpected error occurred."
        print(f"Error: {error}")

    if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print('------')

bot.run(os.getenv('DISCORD_TOKEN'))
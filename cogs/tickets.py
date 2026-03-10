import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

def get_support_role_id(guild_id):
    conn = sqlite3.connect('server_settings.db')
    cursor = conn.cursor()
    cursor.execute('SELECT support_role_id FROM settings WHERE guild_id = ?', (guild_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

class TicketControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, custom_id="claim_ticket_btn", emoji="🙋")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = get_support_role_id(interaction.guild.id)
        support_role = interaction.guild.get_role(role_id) if role_id else None
        
        if (support_role not in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only support staff can claim tickets.", ephemeral=True)
            return

        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"✅ {interaction.user.mention} has claimed this ticket.")

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            creator_id = int(interaction.channel.topic)
            creator = interaction.client.get_user(creator_id) or await interaction.client.fetch_user(creator_id)
            if creator:
                try: await creator.send(f"Your support ticket in **{interaction.guild.name}** has been closed. Thank you!")
                except discord.Forbidden: pass 
        except: pass 

        await interaction.channel.delete(reason=f"Closed by {interaction.user.name}")


class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Touch Me", style=discord.ButtonStyle.success, emoji="🎫", custom_id="permanent_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        role_id = get_support_role_id(interaction.guild.id)
        support_role = interaction.guild.get_role(role_id) if role_id else None
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_id = str(interaction.id)[-4:]
        ticket_channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}-{ticket_id}",
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        embed = discord.Embed(title="🎫 Ticket Opened", description=f"Welcome {interaction.user.mention}!", color=discord.Color.green())
        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=TicketControlsView())
        await interaction.followup.send(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketButton())
        self.bot.add_view(TicketControlsView())

    @app_commands.command(name="setup_tickets", description="Creates the permanent ticket panel.")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📬 Open Ticket for Queries", description="Open ticket with moderators and get your problems cleared.", color=discord.Color.blue())
        await interaction.channel.send(embed=embed, view=TicketButton())
        await interaction.response.send_message("Panel created!", ephemeral=True)

    @app_commands.command(name="add_member", description="Adds a user to the current ticket.")
    async def add_member(self, interaction: discord.Interaction, member: discord.Member):
        if "ticket-" not in interaction.channel.name:
            await interaction.response.send_message("❌ Use this inside a ticket.", ephemeral=True)
            return
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"✅ {member.mention} added.")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
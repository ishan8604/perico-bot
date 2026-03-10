import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio

# --- 1. TICKET CONTROLS (Claim & Close) ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, emoji="🙋‍♂️", custom_id="claim_ticket_btn")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Fetch support role to verify if the user can claim
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT support_role_id FROM ticket_config WHERE guild_id = ?', (interaction.guild.id,))
        res = cursor.fetchone()
        conn.close()

        support_role_id = res[0] if res else None
        
        # Only allow people with the support role (or Admin) to claim
        if support_role_id and not any(role.id == support_role_id for role in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Only support staff can claim tickets!", ephemeral=True)

        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send(f"✅ {interaction.user.mention} has claimed this ticket and will assist you shortly.")
        
        try:
            await interaction.channel.edit(name=f"claimed-{interaction.user.name}")
        except:
            pass

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing ticket and sending DM...", ephemeral=True)
        
        # DM the user before deleting
        try:
            # Logic: ticket-username -> extracts 'username'
            owner_name = interaction.channel.name.replace("ticket-", "").replace("claimed-", "")
            owner = discord.utils.get(interaction.guild.members, name=owner_name)
            
            if owner:
                embed = discord.Embed(
                    title="Ticket Closed",
                    description=f"Your ticket in **{interaction.guild.name}** has been closed.\n**Closed by:** {interaction.user.display_name}",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                await owner.send(embed=embed)
        except Exception as e:
            print(f"Could not DM user: {e}")

        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 2. OPEN TICKET BUTTON ---
class CreateTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Open Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="open_ticket_btn")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        # Fetch Support Role ID
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT support_role_id FROM ticket_config WHERE guild_id = ?', (guild.id,))
        result = cursor.fetchone()
        conn.close()

        support_role_id = result[0] if result else None
        support_role = guild.get_role(support_role_id) if support_role_id else None

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

        # Create Channel
        channel = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)

        # MENTION LOGIC: This ensures the support role actually gets a notification
        ping_content = f"{user.mention}"
        if support_role:
            ping_content += f" {support_role.mention}"

        embed = discord.Embed(
            title="🎫 Support Ticket Created",
            description=f"Hello {user.mention}, thank you for reaching out!\n\n**Staff:** Use the buttons below to claim or close this ticket.",
            color=discord.Color.blue()
        )

        # Send the ping and the view
        await channel.send(content=ping_content, embed=embed, view=TicketControls())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# --- 3. PERSISTENT VIEW ---
class PersistentTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CreateTicketButton())

# --- 4. THE COG ---
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('server_settings.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('CREATE TABLE IF NOT EXISTS ticket_config (guild_id INTEGER PRIMARY KEY, support_role_id INTEGER)')
        self.conn.commit()

    async def cog_load(self):
        # Register views for persistence
        self.bot.add_view(PersistentTicketView())
        self.bot.add_view(TicketControls())

    @app_commands.command(name="set_support_role", description="Select the role that will be pinged for new tickets.")
    @app_commands.default_permissions(administrator=True)
    async def set_support_role(self, interaction: discord.Interaction, role: discord.Role):
        self.cursor.execute('INSERT OR REPLACE INTO ticket_config (guild_id, support_role_id) VALUES (?, ?)', (interaction.guild.id, role.id))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Support role set to {role.mention}. This role will now be pinged in new tickets.", ephemeral=True)

    @app_commands.command(name="setup_tickets", description="Post the ticket creation panel.")
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📩 Touch Me",
            description="Need help. Open a ticket with admins to discuss the problems.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message("Ticket panel deployed!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=PersistentTicketView())

    @app_commands.command(name="add_member", description="Add a specific member to this ticket channel.")
    @app_commands.describe(member="The member you want to add to this ticket")
    async def add_member(self, interaction: discord.Interaction, member: discord.Member):
        # 1. Security Check: Only allow this in ticket channels
        if not interaction.channel.name.startswith(("ticket-", "claimed-")):
            return await interaction.response.send_message("❌ This command can only be used inside a ticket channel!", ephemeral=True)

        # 2. Permission Check: Only staff or admins should be able to add people
        conn = sqlite3.connect('server_settings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT support_role_id FROM ticket_config WHERE guild_id = ?', (interaction.guild.id,))
        res = cursor.fetchone()
        conn.close()

        support_role_id = res[0] if res else None
        is_staff = any(role.id == support_role_id for role in interaction.user.roles) if support_role_id else False
        
        if not is_staff and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Only support staff can add members to tickets!", ephemeral=True)

        # 3. Update Permissions
        await interaction.channel.set_permissions(member, 
            read_messages=True, 
            send_messages=True, 
            attach_files=True, 
            embed_links=True,
            view_channel=True
        )
        
        # 4. Success Message
        embed = discord.Embed(
            description=f"✅ {member.mention} has been added to the ticket by {interaction.user.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
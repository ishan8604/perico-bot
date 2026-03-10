import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Connect to a new database specifically for roles
        self.conn = sqlite3.connect('roles.db')
        self.cursor = self.conn.cursor()
        
        # Create a table to store each server's specific roles
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_roles (
                guild_id INTEGER,
                role_id INTEGER,
                description TEXT,
                emoji TEXT,
                PRIMARY KEY (guild_id, role_id)
            )
        ''')
        self.conn.commit()

    # --- 1. Commands to Manage the Roles List ---

    @app_commands.command(name="add_role", description="Add a role to this server's dropdown menu.")
    @app_commands.default_permissions(administrator=True)
    async def add_role(self, interaction: discord.Interaction, role: discord.Role, description: str, emoji: str = None):
        # Discord limits dropdowns to 25 options. Let's make sure they don't exceed that.
        self.cursor.execute('SELECT COUNT(*) FROM server_roles WHERE guild_id = ?', (interaction.guild.id,))
        count = self.cursor.fetchone()[0]
        
        if count >= 25:
            await interaction.response.send_message("❌ You can only have a maximum of 25 roles in a single dropdown menu.", ephemeral=True)
            return

        # Insert or update the role in the database
        self.cursor.execute('''
            INSERT OR REPLACE INTO server_roles (guild_id, role_id, description, emoji)
            VALUES (?, ?, ?, ?)
        ''', (interaction.guild.id, role.id, description, emoji))
        self.conn.commit()
        
        await interaction.response.send_message(f"✅ Added {role.mention} to the dropdown list!\n*Note: You must run `/setup_roles` again to update the visual menu.*", ephemeral=True)

    @app_commands.command(name="remove_role", description="Remove a role from this server's dropdown menu.")
    @app_commands.default_permissions(administrator=True)
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role):
        self.cursor.execute('DELETE FROM server_roles WHERE guild_id = ? AND role_id = ?', (interaction.guild.id, role.id))
        self.conn.commit()
        
        await interaction.response.send_message(f"🗑️ Removed {role.mention} from the dropdown list.\n*Note: You must run `/setup_roles` again to update the visual menu.*", ephemeral=True)

    # --- 2. Command to Generate the Menu ---

    @app_commands.command(name="setup_roles", description="Generates the self-assignable roles menu in the current channel.")
    @app_commands.default_permissions(administrator=True)
    async def setup_roles(self, interaction: discord.Interaction):
        # Fetch all roles saved for this specific server
        self.cursor.execute('SELECT role_id, description, emoji FROM server_roles WHERE guild_id = ?', (interaction.guild.id,))
        saved_roles = self.cursor.fetchall()
        
        if not saved_roles:
            await interaction.response.send_message("❌ You haven't added any roles yet! Use `/add_role` first.", ephemeral=True)
            return

        # Build the dynamic options list
        options = []
        for row in saved_roles:
            role_id, desc, emoji = row
            role = interaction.guild.get_role(role_id)
            
            # If the role was deleted from the server, skip it
            if not role:
                continue 
                
            options.append(
                discord.SelectOption(label=role.name, description=desc, emoji=emoji, value=str(role.id))
            )

        if not options:
            await interaction.response.send_message("❌ None of the saved roles exist in the server anymore.", ephemeral=True)
            return

        # Create the dynamic dropdown
        select = discord.ui.Select(
            custom_id="dynamic_role_dropdown", # This static ID is how we catch the clicks later!
            placeholder="Select your roles...",
            min_values=0,
            max_values=len(options),
            options=options
        )
        
        view = discord.ui.View(timeout=None)
        view.add_item(select)
        
        embed = discord.Embed(
            title="🎭 Get Your Roles Here",
            description="Click on Drop down menu to get roles according to your preference.",
            color=discord.Color.teal()
        )
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("Role menu successfully generated!", ephemeral=True)

    # --- 3. The Listener to Process Clicks ---

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # We only care about interactions that are components (like buttons/dropdowns)
        if interaction.type != discord.InteractionType.component:
            return
            
        # Check if the interaction is from our specific role dropdown
        if interaction.data.get("custom_id") == "dynamic_role_dropdown":
            await interaction.response.defer(ephemeral=True)
            
            # Get the role IDs the user just selected from the dropdown
            selected_role_ids = [int(val) for val in interaction.data.get("values", [])]
            
            # Fetch the total list of available roles for this server from the database
            self.cursor.execute('SELECT role_id FROM server_roles WHERE guild_id = ?', (interaction.guild.id,))
            managed_role_ids = [row[0] for row in self.cursor.fetchall()]
            
            added_roles = []
            removed_roles = []
            
            for role_id in managed_role_ids:
                role = interaction.guild.get_role(role_id)
                if not role:
                    continue
                    
                # If they selected it, and don't have it yet -> Add it
                if role_id in selected_role_ids and role not in interaction.user.roles:
                    try:
                        await interaction.user.add_roles(role)
                        added_roles.append(role.mention)
                    except discord.Forbidden:
                        await interaction.followup.send(f"❌ I don't have permission to give out the {role.mention} role. Check my role hierarchy!", ephemeral=True)
                        return
                        
                # If they unchecked it, and currently have it -> Remove it
                elif role_id not in selected_role_ids and role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role)
                        removed_roles.append(role.mention)
                    except discord.Forbidden:
                        pass
            
            # Send a summary of changes
            if added_roles or removed_roles:
                response_msg = "✅ **Your roles have been updated!**\n"
                if added_roles:
                    response_msg += f"**Added:** {', '.join(added_roles)}\n"
                if removed_roles:
                    response_msg += f"**Removed:** {', '.join(removed_roles)}\n"
            else:
                response_msg = "No changes were made to your roles."
                
            await interaction.followup.send(response_msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
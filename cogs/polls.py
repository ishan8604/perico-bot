import discord
from discord.ext import commands
from discord import app_commands

class PollView(discord.ui.View):
    def __init__(self, question, options):
        super().__init__(timeout=None) # Make it persistent
        self.question = question
        self.options = options
        self.votes = {option: [] for option in options} # { "Option Name": [user_id1, user_id2] }

        # Dynamically create buttons for each option
        for option in self.options:
            self.add_item(PollButton(label=option))

    def create_embed(self):
        embed = discord.Embed(title=f"📊 Poll: {self.question}", color=discord.Color.blue())
        total_votes = sum(len(v) for v in self.votes.values())
        
        description = ""
        for option, voters in self.votes.items():
            count = len(voters)
            # Calculate percentage bar
            percent = (count / total_votes * 100) if total_votes > 0 else 0
            bar = "🟦" * int(percent / 10) + "⬜" * (10 - int(percent / 10))
            description += f"**{option}**\n{bar} {count} votes ({int(percent)}%)\n\n"
        
        embed.description = description
        embed.set_footer(text=f"Total Votes: {total_votes}")
        return embed

class PollButton(discord.ui.Button):
    def __init__(self, label):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"poll_{label}")

    async def callback(self, interaction: discord.Interaction):
        view: PollView = self.view
        user_id = interaction.user.id

        # 1. Check if the user has already voted for ANY option
        for option, voters in view.votes.items():
            if user_id in voters:
                # If they click the same button, let's remove their vote (Toggle)
                if option == self.label:
                    view.votes[option].remove(user_id)
                    await interaction.response.edit_message(embed=view.create_embed())
                    return
                else:
                    # If they try to vote for a different option, deny them (or you could switch their vote)
                    await interaction.response.send_message("❌ You have already voted! Click your original choice to remove it first.", ephemeral=True)
                    return

        # 2. Add the new vote
        view.votes[self.label].append(user_id)
        await interaction.response.edit_message(embed=view.create_embed())

class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Create a poll with up to 5 options.")
    @app_commands.describe(
        question="The topic of the poll",
        option1="First choice",
        option2="Second choice",
        option3="Third choice (optional)",
        option4="Fourth choice (optional)",
        option5="Fifth choice (optional)"
    )
    @app_commands.default_permissions(administrator=True) # Admin only
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None):
        # Filter out None options
        options = [opt for opt in [option1, option2, option3, option4, option5] if opt is not None]
        
        if len(options) < 2:
            await interaction.response.send_message("❌ You need at least 2 options for a poll!", ephemeral=True)
            return

        view = PollView(question, options)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

async def setup(bot):
    await bot.add_cog(Polls(bot))
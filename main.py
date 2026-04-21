import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

MODMAIL_CHANNEL_ID = int(os.getenv("MODMAIL_CHANNEL_ID"))

# In-memory storage (no database)
active_threads = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 📩 User DM → create/send to modmail thread
    if isinstance(message.channel, discord.DMChannel):
        guild = bot.guilds[0]
        modmail_channel = guild.get_channel(MODMAIL_CHANNEL_ID)

        thread = active_threads.get(message.author.id)

        if thread is None:
            thread = await modmail_channel.create_thread(
                name=f"modmail-{message.author}",
                type=discord.ChannelType.private_thread
            )
            active_threads[message.author.id] = thread

            await thread.send(f"📨 New modmail from {message.author} ({message.author.id})")

        await thread.send(message.content)

    # 💬 Staff reply → send back to user
    elif isinstance(message.channel, discord.Thread):
        for user_id, thread in active_threads.items():
            if thread.id == message.channel.id:
                user = await bot.fetch_user(user_id)
                await user.send(message.content)
                break

    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))

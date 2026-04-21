import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

MODMAIL_CHANNEL_ID = int(os.getenv("MODMAIL_CHANNEL_ID"))

active_threads = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # 📩 DM → modmail
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

            await thread.send(f"📨 New ticket from {message.author} ({message.author.id})")
            await message.author.send("✅ Your message has been sent to the moderators.")

        # send message + attachments
        content = message.content or ""
        files = [await a.to_file() for a in message.attachments]

        await thread.send(content, files=files)

    # 💬 Staff → user
    elif isinstance(message.channel, discord.Thread):
        if message.channel.parent_id != MODMAIL_CHANNEL_ID:
            return  # ignore other threads

        # find user
        user_id = None
        for uid, thread in active_threads.items():
            if thread.id == message.channel.id:
                user_id = uid
                break

        if user_id:
            user = await bot.fetch_user(user_id)

            files = [await a.to_file() for a in message.attachments]
            await user.send(message.content, files=files)

    await bot.process_commands(message)

# ❌ Close command
@bot.command()
async def close(ctx):
    if not isinstance(ctx.channel, discord.Thread):
        return

    # find user
    user_id = None
    for uid, thread in active_threads.items():
        if thread.id == ctx.channel.id:
            user_id = uid
            break

    if user_id:
        user = await bot.fetch_user(user_id)
        await user.send("🔒 Your modmail ticket has been closed.")

        del active_threads[user_id]

    await ctx.send("✅ Ticket closed.")
    await ctx.channel.delete()

bot.run(os.getenv("TOKEN"))

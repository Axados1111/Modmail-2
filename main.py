import discord
from discord.ext import commands
import os
import sqlite3

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

MODMAIL_CHANNEL_ID = int(os.getenv("MODMAIL_CHANNEL_ID"))

# 🗄️ SQLite setup
conn = sqlite3.connect("modmail.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    user_id INTEGER PRIMARY KEY,
    thread_id INTEGER
)
""")
conn.commit()


def get_thread(user_id):
    cursor.execute("SELECT thread_id FROM tickets WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None


def add_ticket(user_id, thread_id):
    cursor.execute("REPLACE INTO tickets (user_id, thread_id) VALUES (?, ?)", (user_id, thread_id))
    conn.commit()


def remove_ticket(user_id):
    cursor.execute("DELETE FROM tickets WHERE user_id = ?", (user_id,))
    conn.commit()


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

        thread_id = get_thread(message.author.id)

        if thread_id:
            thread = guild.get_thread(thread_id)
        else:
            thread = await modmail_channel.create_thread(
                name=f"modmail-{message.author}",
                type=discord.ChannelType.private_thread
            )
            add_ticket(message.author.id, thread.id)

            await thread.send(f"📨 New ticket from {message.author} ({message.author.id})")
            await message.author.send("✅ Your message has been sent to moderators.")

        files = [await a.to_file() for a in message.attachments]
        await thread.send(message.content or "", files=files)

    # 💬 Staff → user
    elif isinstance(message.channel, discord.Thread):
        if message.channel.parent_id != MODMAIL_CHANNEL_ID:
            return

        cursor.execute("SELECT user_id FROM tickets WHERE thread_id = ?", (message.channel.id,))
        result = cursor.fetchone()

        if result:
            user = await bot.fetch_user(result[0])
            files = [await a.to_file() for a in message.attachments]
            await user.send(message.content or "", files=files)

    await bot.process_commands(message)


@bot.command()
async def close(ctx):
    if not isinstance(ctx.channel, discord.Thread):
        return

    cursor.execute("SELECT user_id FROM tickets WHERE thread_id = ?", (ctx.channel.id,))
    result = cursor.fetchone()

    if result:
        user_id = result[0]
        user = await bot.fetch_user(user_id)

        await user.send("🔒 Your ticket has been closed.")
        remove_ticket(user_id)

    await ctx.send("✅ Ticket closed.")
    await ctx.channel.delete()


bot.run(os.getenv("TOKEN"))

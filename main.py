import os
import discord
from discord.ext import commands
import aiohttp
import io

TOKEN = os.environ.get("DISCORD_TOKEN")
DESTINATION_CHANNEL_ID = 1378860563748098048
IGNORED_ROLE_NAMES = ["Bot 🤖"]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

def has_ignored_role(member):
    return any(role.name in IGNORED_ROLE_NAMES for role in member.roles)

def format_base(message):
    user = (
        f"{message.author.name}"
        if message.author.discriminator == "0"
        else f"{message.author.name}#{message.author.discriminator}"
    )
    msg_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
    return f"{user} | {msg_link}"

def format_embeds(message):
    parts = []
    for i, embed in enumerate(message.embeds[:3], 1):
        title = embed.title or ""
        desc = embed.description or ""
        parts.append(f"[EMBED {i}] {title} {desc}")
    return " ".join(parts)

def flatten_message(message):
    text = message.content or ""
    text += " " + format_embeds(message)
    return discord.utils.escape_mentions(text.strip())

async def download_attachments(attachments):
    files = []
    async with aiohttp.ClientSession() as session:
        for attachment in attachments[:5]:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    fp = io.BytesIO(data)
                    files.append(discord.File(fp, filename=attachment.filename))
    return files

async def find_log_message(channel, msg_id):
    async for msg in channel.history(limit=100):
        if f"/{msg_id}" in msg.content:
            return msg
    return None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if (
        message.guild is None
        or message.author == bot.user
        or message.is_system()
        or has_ignored_role(message.author)
    ):
        return

    dest = bot.get_channel(DESTINATION_CHANNEL_ID)
    if dest:
        content = flatten_message(message)
        files = await download_attachments(message.attachments)
        await dest.send(f"{format_base(message)} | {content}", files=files)

    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if (
        after.guild is None
        or after.author == bot.user
        or after.is_system()
        or has_ignored_role(after.author)
    ):
        return

    dest = bot.get_channel(DESTINATION_CHANNEL_ID)
    if not dest:
        return

    before_content = flatten_message(before)
    after_content = flatten_message(after)
    log_line = f"{format_base(after)} | BEFORE: {before_content} → AFTER: {after_content}"

    files = await download_attachments(after.attachments)
    ref = await find_log_message(dest, after.id)
    if ref:
        await ref.reply(log_line, files=files)
    else:
        await dest.send(log_line, files=files)

@bot.event
async def on_message_delete(message):
    if (
        message.guild is None
        or message.author == bot.user
        or message.is_system()
        or has_ignored_role(message.author)
    ):
        return

    dest = bot.get_channel(DESTINATION_CHANNEL_ID)
    if not dest:
        return

    content = flatten_message(message)
    log_line = f"{format_base(message)} | DELETED: {content}"

    files = await download_attachments(message.attachments)
    ref = await find_log_message(dest, message.id)
    if ref:
        await ref.reply(log_line, files=files)
    else:
        await dest.send(log_line, files=files)

bot.run(TOKEN)
import asyncio
import os
import re

from telegram import Bot


# NOTE: You need to initiate a conversation with the bot before it can send you messages
# get bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Send a message to @userinfobot to obtain this
USER_ID = os.getenv("USER_ID")


def send_message(msg: str):
    bot = Bot(token=BOT_TOKEN)
    msg = re.sub(r"([_*[\]()~`>#\+\-=|{}.!])", r"\\\1", msg)
    asyncio.run(bot.send_message(chat_id=USER_ID, text=f"```\n{msg}\n```", parse_mode="MarkdownV2"))

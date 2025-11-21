import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

bot = Bot(token=os.environ.get('TELEGRAM_TOKEN', 'placeholder'))

def get_join_keyboard():
    """Return inline keyboard for joining game"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Join Game", callback_data="join"),
            InlineKeyboardButton("Add AI", callback_data="add_ai")
        ]
    ])

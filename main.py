from src.commands import bot, check_inactive_channels
from src.settings import TOKEN, ENV_REF
from src.keep_alive import keep_alive

if __name__ == '__main__':
    if ENV_REF == 'replit':
        keep_alive()
    bot.loop.create_task(check_inactive_channels())
    bot.ticket_categories = {}  # Dictionary to store ticket categories
    bot.run(TOKEN)

    

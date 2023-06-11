from src.commands import bot, check_inactive_channels
from src.settings import TOKEN

if __name__ == '__main__':
    bot.loop.create_task(check_inactive_channels())
    bot.ticket_categories = {}  # Dictionary to store ticket categories
    bot.run(TOKEN)

    

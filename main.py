from src.commands import bot, check_inactive_channels
from src.settings import TOKEN, ENV_REF, VERSION
from src.keep_alive import keep_alive


banner = r'''
_______________________________________
  ____            __            _     
 /_  / ___ ____  / /  __ ______(_)__ _
  / /_/ _ `/ _ \/ _ \/ // / __/ / _ `/
 /___/\_,_/ .__/_//_/\_, /_/ /_/\_,_/ 
         /_/        /___/            
_______________________________________
'''

if __name__ == '__main__':
    if ENV_REF == 'replit':
        keep_alive()

    print(banner)
    print(f'Version: {VERSION}')

    bot.loop.create_task(check_inactive_channels())
    bot.ticket_categories = {}  # Dictionary to store ticket categories
    bot.run(TOKEN)

    

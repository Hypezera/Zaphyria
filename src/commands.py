from base64 import b64encode, b64decode
import discord
from discord.ext import commands
import asyncio
import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import numpy as np
import aiohttp
from src.database import DbHandler
from src.settings import DATABASE


intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

ticket_channels = {}  # Dicionário para armazenar os canais de ticket e o tempo da última mensagem



@bot.event 
async def on_ready():
    activity = discord.Game(name='A perfect help for your server!', type=3)
    await bot.change_presence(status=discord.Status.online, activity=activity) 
    '''
    ao vivo -> activity = discord.Streaming(name="ola mundo", url="twitch_url")
    ouvindo -> activity = discord.Activity(type=discord.ActivityType.listening, name="ola mundo")
    assistindo -> activity = discord.Activity(type=discord.ActivityType.watching, name="ola mundo")
    '''
    print('Pronto para uso!\n') 
    print(f'Nome: {bot.user}\n')

    
@bot.event
async def on_message(message):
    db = DbHandler(DATABASE)
    user_id = str(message.author.id)
    if not db.view_profile(user_id):
        db.create_profile(user_id)
    db.connection.close()
    if isinstance(message.channel, discord.TextChannel) and message.channel.id in ticket_channels:
        ticket_channels[message.channel.id] = datetime.datetime.now()  # Atualizar o tempo da última mensagem no canal
    await bot.process_commands(message)


async def check_inactive_channels():
    while True:
        await asyncio.sleep(5)  # Aguardar 5 segundos antes de verificar a inatividade dos canais
        now = datetime.datetime.now()
        inactive_channels = [channel_id for channel_id, last_message_time in ticket_channels.items()
                             if (now - last_message_time).total_seconds() > 5]
        for channel_id in inactive_channels:
            ticket_channel = bot.get_channel(channel_id)
            if ticket_channel:
                await ticket_channel.delete(reason='Ticket apagado por inatividade')
                del ticket_channels[channel_id]


# bot.loop.create_task(check_inactive_channels())


@bot.slash_command(name='ticket', description='Create a support ticket')
async def ticket(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True),
        bot.user: discord.PermissionOverwrite(read_messages=True)
    }

    ticket_category_id = bot.ticket_categories.get(ctx.guild.id)
    ticket_category = ctx.guild.get_channel(ticket_category_id)

    if not ticket_category:
        await ctx.respond('The ticket category has not been configured.', ephemeral=True)
        return

    ticket_channel = await ticket_category.create_text_channel(f'ticket-{ctx.author.name}', overwrites=overwrites)
    await ctx.respond(f'{ctx.author.mention}, your ticket has been created in {ticket_channel.mention}', ephemeral=True)

    ticket_message_content = 'Click on the reaction below to close the ticket.'
    ticket_message = await ticket_channel.send(ticket_message_content)
    await ticket_message.add_reaction('🔒')

    def check(reaction, user):
        return str(reaction.emoji) == '🔒' and user != bot.user and reaction.message == ticket_message

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=3600, check=check)
        if str(reaction.emoji) == '🔒':
            await ticket_channel.delete(reason='Ticket closed by user')
    except asyncio.TimeoutError:
        pass


@bot.slash_command(name='setcategory', description='Define the category for ticket channels')
@commands.has_permissions(administrator=True)
async def set_category(ctx, category: discord.CategoryChannel):
    bot.ticket_categories[ctx.guild.id] = category.id
    await ctx.respond(f'The category for tickets has been set to {category.name}', ephemeral=True)


@set_category.error
async def set_category_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond('You need to have administrator permission to use this command.', ephemeral=True)
    else:
        await ctx.respond('An error occurred while executing the command.', ephemeral=True)


@bot.slash_command(name='info', description='Show bot information')
async def info(ctx):
    info_text = """
    Hello! I am a support bot. I'm here to help you create and manage support tickets in your Discord server.
    
    With the `/ticket` command, you can create a support ticket and receive an exclusive channel for communication with the support team.
    
    Use the `/setcategory` command to define the category where ticket channels will be created.
    Note: This command can only be used by an administrator!

    Use the `/clear_messages` command to delete messages in the current channel.
    Note: To use this command, you need the permission to manage messages!
    
    Use the `/avatar` command to view user avatars!

    I hope to assist with all your support needs!
    """

    await ctx.respond(info_text, ephemeral=True)


@bot.slash_command(name='clear_messages', description='Delete messages in the current channel')
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int):
    if amount < 1 or amount > 99:
        await ctx.respond('Invalid number. Please specify a number from 1 to 99.', ephemeral=True)
        return

    channel = ctx.channel
    messages = []

    async for message in channel.history(limit=amount + 1):
        messages.append(message)

    while len(messages) > 0:
        if len(messages) > 100:
            batch = messages[:100]
            messages = messages[100:]
        else:
            batch = messages
            messages = []

        await channel.delete_messages(batch)

    await ctx.respond(f"{amount} messages have been successfully deleted.", ephemeral=True)


@clear_messages.error
async def clear_messages_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond('You need the permission to manage messages to use this command.', ephemeral=True)
    else:
        await ctx.respond('An error occurred while executing the command.', ephemeral=True)


# bot.ticket_categories = {}  # Dictionary to store ticket categories


@bot.slash_command(name='avatar', description="Show a user's profile picture")
async def avatar_command(ctx, user: discord.Member = None):
    if not user:
        user = ctx.author

    avatar_url = user.avatar.url

    embed = discord.Embed(title="Avatar", color=discord.Color.blue())
    embed.set_image(url=avatar_url)

    await ctx.respond(embed=embed, ephemeral=True)


@bot.slash_command(name='support', description='Send a support link via direct message')
async def support(ctx):
    try:
        await ctx.author.send('Here is the support link: https://discord.gg/r74dfv3AJD')
        await ctx.respond('Support message sent via direct message!', ephemeral=True)
    except discord.Forbidden:
        await ctx.respond('Unable to send the message via direct message. Please check your privacy settings.', ephemeral=True)


@bot.slash_command(name='edit_ticket', description='Edit the name of a ticket channel')
async def edit_ticket(ctx, new_name: str):
    ticket_category_id = bot.ticket_categories.get(ctx.guild.id)
    ticket_category = ctx.guild.get_channel(ticket_category_id)

    if not ticket_category:
        await ctx.respond('The ticket category has not been configured.', ephemeral=True)
        return

    ticket_channel = None
    for channel in ticket_category.text_channels:
        if channel.permissions_for(ctx.author).read_messages and channel.name.startswith('ticket-'):
            ticket_channel = channel
            break

    if not ticket_channel:
        await ctx.respond('You do not have a ticket channel to edit.', ephemeral=True)
        return

    await ticket_channel.edit(name=new_name)
    await ctx.respond(f'The ticket channel name has been updated to {new_name}.', ephemeral=True)


@bot.slash_command(name='add_role', description='Assign a role to a user')
@commands.has_permissions(manage_roles=True)
async def add_role(ctx, user: discord.Member, role: discord.Role):
    await user.add_roles(role)
    await ctx.respond(f'The role {role.name} has been assigned to {user.display_name}', ephemeral=True)


@add_role.error
async def add_role_error(ctx, error): 
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond('You need to have the "Manage Roles" permission to use this command.', ephemeral=True)
    else:
        await ctx.respond('An error occurred while executing the command.', ephemeral=True)


@bot.slash_command(name='profile', description='Mostra o perfil do usuário')
async def profile(ctx, user: discord.Member = None):
    if not user:
        user = ctx.author

    avatar_url = user.avatar.url
    nickname = user.display_name

    profile_image = await create_profile_image(avatar_url, nickname, user.id)

    file = discord.File(profile_image, filename='profile.png')
    await ctx.respond(file=file)


@bot.slash_command(name='bio', description='Define a bio do perfil')
async def set_bio(ctx, bio: str):
    user_id = ctx.author.id

    if len(bio) > 150:
        await ctx.respond("A bio deve ter no máximo 150 caracteres.", ephemeral=True)
        return

    # Quebrar a bio em linhas de até 35 caracteres
    lines = []
    while len(bio) > 35:
        line = bio[:35]
        lines.append(line)
        bio = bio[35:]
    lines.append(bio)

    # Juntar as linhas com quebras de linha
    formatted_bio = '\n'.join(lines)
    db = DbHandler(DATABASE)
    db.update_bio(str(user_id), formatted_bio)
    # user_biographies[user_id] = formatted_bio
    db.connection.close()
    await ctx.respond("Bio definida com sucesso!", ephemeral=True)


@bot.slash_command(name='badge', description='Define o distintivo do perfil')
async def set_badge(ctx, badge: str):
    user_id = ctx.author.id

    if badge == "Redphyria":
        badge_url = 'https://cdn.discordapp.com/attachments/1102272897822756987/1117176500752486510/redlink.png'
    elif badge == "GreenStar":
        badge_url = 'https://cdn.discordapp.com/attachments/1102272897822756987/1117176737890046042/Green_link.png'
    else:
        await ctx.respond("Distintivo inválido.", ephemeral=True)
        return

    # badge_data = await fetch_image(badge_url)
    badge_data = b64encode(str(badge_url).encode('utf-8')).decode('utf-8')
    db = DbHandler(DATABASE)
    db.update_badge(str(user_id), badge_data)
    # user_badges[user_id] = badge_data
    db.connection.close()
    await ctx.respond("Distintivo definido com sucesso!", ephemeral=True)


async def create_profile_image(avatar_url, nickname, user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(str(avatar_url)) as response:
            avatar_data = await response.read()

    avatar_image = Image.open(BytesIO(avatar_data))

    # Redimensionar a imagem de perfil
    avatar_image = avatar_image.resize((230, 230))

    # Criar uma máscara circular
    mask = Image.new('L', avatar_image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar_image.size[0], avatar_image.size[1]), fill=255)

    # Aplicar a máscara à imagem de perfil
    avatar_image.putalpha(mask)

    # Criar uma nova imagem com fundo sólido e barra de menu
    background_color = (29, 29, 27)  # Cor em RGB: #1d1d1b
    menu_bar_color = (23, 23, 21)  # Cor em RGB: #171715
    profile_image = Image.new('RGB', (1080, 720), background_color)

    # Desenhar a barra de menu
    menu_bar_height = 100
    menu_bar = Image.new('RGB', (1080, menu_bar_height), menu_bar_color)
    profile_image.paste(menu_bar, (0, 0))

    # Colocar a imagem de perfil circular na nova imagem
    profile_image.paste(avatar_image, (50, (menu_bar_height + 20)), mask=avatar_image)

    draw = ImageDraw.Draw(profile_image)
    font_size = int(avatar_image.size[1] / 6)  # Tamanho proporcional da fonte
    
    try:
        font = ImageFont.truetype('arial.ttf', font_size)
    except OSError:
        font = ImageFont.load_default()

    # Verificar se o usuário tem o perfil verificado
    verified_users = [978492950105432094, 832290124506333194, 588796628929085463, 269539802292944896]  # IDs dos usuários verificados
    if user_id in verified_users:
        verified_icon_url = 'https://cdn.discordapp.com/attachments/1104634375699710003/1115445549840224286/dourado.png'
        verified_icon_data = await fetch_image(verified_icon_url)
        verified_icon = Image.open(BytesIO(verified_icon_data))
        verified_icon_size = (font_size, font_size)
        verified_icon = verified_icon.resize(verified_icon_size)

        # Calcular a posição do ícone verificado
        verified_icon_x = 235 + avatar_image.size[0] + -65
        verified_icon_y = menu_bar_height + -20 + ((avatar_image.size[1] - verified_icon_size[1]) // 2)

        # Posicionar o ícone verificado
        profile_image.paste(verified_icon, (verified_icon_x, verified_icon_y), mask=verified_icon)

    # Verificar se o usuário tem o perfil de developer
    developers_users = [978492950105432094, 269539802292944896]  # IDs dos usuários verificados
    if user_id in developers_users:
        developer_icon_url = 'https://cdn.discordapp.com/attachments/1115858129486356500/1117219100482089101/link_perfeito.png'
        developer_icon_data = await fetch_image(developer_icon_url)
        developer_icon = Image.open(BytesIO(developer_icon_data))
        developer_icon_size = (font_size, font_size)
        developer_icon = developer_icon.resize(developer_icon_size)

        # Calcular a posição do ícone developer
        developer_icon_x = 235 + avatar_image.size[0] + -120
        developer_icon_y = menu_bar_height + -20 + ((avatar_image.size[1] - developer_icon_size[1]) // 2)

        # Posicionar o ícone de developer
        profile_image.paste(developer_icon, (developer_icon_x, developer_icon_y), mask=developer_icon)

    # Calcular a posição do nickname
    nickname_x = 55 + avatar_image.size[0] + 10
    nickname_y = menu_bar_height + 20 + ((avatar_image.size[1] - font_size) // 2)

    draw.text((nickname_x, nickname_y), nickname, (201, 201, 200), font=font)

    # Adicionar a string "Bio" acima dos status
    bio_x = -120 + avatar_image.size[0] + 10
    bio_y = menu_bar_height + 340

    bio_text = "biography:"
    draw.text((bio_x, bio_y), bio_text, (63, 63, 56), font=font)

    # Recupera dados do usuário do banco de dados
    db = DbHandler(DATABASE)
    db_profile = db.view_profile(str(user_id))


    # Verificar se o usuário tem um status personalizado
    if db_profile:
        _, badge_data, bio = db_profile
        badge_data = b64decode(badge_data).decode('utf-8')
        badge_data = await fetch_image(badge_data)
    else:
        badge_data, bio = None, ''

    # Calcular a posição do status
    bio_x = -120 + avatar_image.size[0] + 10
    bio_y = menu_bar_height + 130 + avatar_image.size[1] + 20

    draw.text((bio_x, bio_y), bio, (201, 201, 200), font=font)

    if badge_data:
        badge_image = Image.open(BytesIO(badge_data))
        badge_image_size = (font_size, font_size)
        badge_image = badge_image.resize(badge_image_size)

        # Calcular a posição do distintivo
        badge_x = 235 + avatar_image.size[0] + -175
        badge_y = menu_bar_height + -20 + ((avatar_image.size[1] - badge_image_size[1]) // 2)

        # Posicionar o distintivo
        profile_image.paste(badge_image, (badge_x, badge_y), mask=badge_image)

    # Desenhar a barra inferior
    bottom_bar_height = 20
    bottom_bar_color = (23, 23, 21)  # Cor em RGB: #171715
    bottom_bar = Image.new('RGB', (1080, bottom_bar_height), bottom_bar_color)
    profile_image.paste(bottom_bar, (0, 720 - bottom_bar_height))

    profile_image_bytes = BytesIO()
    profile_image.save(profile_image_bytes, format='PNG')
    profile_image_bytes.seek(0)
    db.connection.close()
    return profile_image_bytes


async def fetch_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()


@bot.slash_command(name='servericon', description='Shows a server icon')
async def server_icon(ctx, server: str):
    try:
        guild = None
        if server.isdigit():
            guild = bot.get_guild(int(server))
        else:
            invite = await bot.fetch_invite(server)
            guild = invite.guild

        if guild is None:
            await ctx.respond("I'm not on this server!", ephemeral=True)
        else:
            icon_url = guild.icon.url if guild.icon else discord.Embed.Empty

            embed = discord.Embed(title="Server Icon!", color=discord.Color.blue())
            embed.set_image(url=icon_url)

            await ctx.respond(embed=embed, ephemeral=True)
    except discord.errors.NotFound:
        await ctx.respond('Invalid invitation or server not found!', ephemeral=True)
    except ValueError:
        await ctx.respond('Invalid Server ID!', ephemeral=True)
    except Exception as e:
        await ctx.respond('An error occurred while executing the command!', ephemeral=True)




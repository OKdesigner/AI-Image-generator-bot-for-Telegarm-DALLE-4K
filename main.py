import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps
from gradio_client import Client  # Add this line back
import time
import random
from config import TOKEN, ADMIN_ID, DEFAULT_NEGATIVE_PROMPT, MAX_SEED, MAX_WIDTH, MAX_HEIGHT
from db import get_db_connection, initialize_database, get_user, create_user, update_user_data
from utils import generate_random_prompt
from logger import logger

bot = telebot.TeleBot(TOKEN)
dalle_client = Client("mukaist/DALLE-4K")  # This line should now work

# Декоратор для проверки пользователя
def check_user(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        username = message.from_user.username
        user = get_user(user_id)
        if not user:
            create_user(user_id, username)
        return func(message, *args, **kwargs)
    return wrapper

def send_welcome_instructions(message):
    welcome_text = (
        "Welcome to the DALLE-4K! 🎨\n"
        "Here's how to get started:\n"
        "1. First, set your generation settings using /settings\n"
        "2. Send a text message with your prompt\n"
        "3. Optionally, set a negative prompt\n"
        "4. Wait for your amazing result!"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu_keyboard())

# Keyboards
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("Create image", callback_data="create_image"))
    keyboard.row(InlineKeyboardButton("Settings", callback_data="settings"))
    keyboard.row(InlineKeyboardButton("Help", callback_data="help"))
    keyboard.row(InlineKeyboardButton("Random prompt", callback_data="random_prompt"))
    return keyboard

# Settings_keyboard function
def settings_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("Style", callback_data="set_style"))
    keyboard.row(InlineKeyboardButton("Size", callback_data="set_size"))
    keyboard.row(InlineKeyboardButton("Guidance Scale", callback_data="set_guidance"))
    keyboard.row(InlineKeyboardButton("Seed", callback_data="set_seed"))
    keyboard.row(InlineKeyboardButton("Back to Main Menu", callback_data="main_menu"))
    return keyboard

def style_keyboard():
    styles = ['3840 x 2160', '2560 x 1440', 'Photo', 'Cinematic', 'Anime', '3D Model', '(No style)']
    keyboard = InlineKeyboardMarkup()
    for style in styles:
        keyboard.row(InlineKeyboardButton(style, callback_data=f"style_{style}"))
    keyboard.row(InlineKeyboardButton("Back", callback_data="settings"))
    return keyboard

def random_prompt_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("Generate", callback_data="generate_random"))
    keyboard.row(InlineKeyboardButton("Generation settings", callback_data="settings"))
    keyboard.row(InlineKeyboardButton("Another prompt", callback_data="another_random"))
    return keyboard

# Command handlers
@bot.message_handler(commands=['start', 'help', 'random', 'generate', 'stats', 'broadcast', 'settings'])
@check_user
def handle_commands(message):
    command = message.text.split()[0][1:]
    if command == 'start':
        send_welcome(message)
    elif command == 'help':
        send_help(message)
    elif command == 'random':
        send_random_prompt(message)
    elif command == 'generate':
        generate_command(message)
    elif command == 'stats':
        send_stats(message)
    elif command == 'broadcast':
        start_broadcast(message)
    elif command == 'settings':
        show_user_settings(message)
    else:
        bot.reply_to(message, "Unknown command. Press /help to see the available commands.")

@bot.message_handler(commands=['start'])
@check_user
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    user = get_user(user_id)
    if user and user[2]:  # Check if user exists and has a prompt set
        bot.reply_to(message, f"Welcome back, {message.from_user.first_name}! Ready to create something amazing?", reply_markup=main_menu_keyboard())
    else:
        send_welcome_instructions(message)
    logger.info(f"User {user_id} ({username}) started the bot")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = "🌟 Welcome to the DALLE-4K, AI Image Generator Bot! 🎨\n\n"
    help_text += "Available commands:\n"
    help_text += "/start - Begin your creative journey\n"
    help_text += "/help - Show this helpful message\n"
    help_text += "/random - Get inspired with a random prompt\n"
    help_text += "/generate - Create an image with your current settings\n"
    help_text += "/settings - Adjust your generation parameters\n\n"
    
    help_text += "🔧 Generation parameters:\n"
    help_text += "• Style - Sets the overall look and feel of your image\n"
    help_text += f"• Size - From 512x512 to {MAX_WIDTH}x{MAX_HEIGHT}, affects detail level\n"
    help_text += "• Guidance Scale (1-20) - Controls how closely the image follows your prompt\n"
    help_text += f"• Seed (0-{MAX_SEED}) - For consistent results across generations\n\n"
    
    help_text += "✨ Tips for writing great prompts:\n"
    help_text += "1. Be specific and descriptive - 'A majestic lion roaring at sunset' is better than just 'A lion'\n"
    help_text += "2. Use style keywords - 'oil painting', 'photorealistic', 'cartoon style'\n"
    help_text += "3. Mention colors, lighting, and mood - 'A cozy cabin in a snowy forest, warm golden light from the windows'\n"
    help_text += "4. Experiment with different art styles - 'cyberpunk cityscape', 'art nouveau portrait'\n"
    help_text += "5. Use commas to separate elements in your prompt\n\n"
    
    help_text += "🎭 Key concepts:\n"
    help_text += "• Prompt - Your description of the image you want to create\n"
    help_text += "• Negative prompt - Things you don't want in your image\n"
    help_text += "• Style - Predefined looks that affect the overall appearance\n"
    help_text += "• Guidance Scale - How strictly the AI follows your prompt\n"
    help_text += "• Seed - A number that determines the initial randomness\n\n"
    
    help_text += "Simply send a text message to use it as a prompt for image generation.\n"
    help_text += "\nIf you need help or have suggestions, feel free to contact @captriphead"
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['random'])
def send_random_prompt(message):
    prompt = generate_random_prompt()
    bot.reply_to(message, f"Here's a creative spark for you:\n\n<code>{prompt}</code>\n\nFeel free to use it as is or add your own twist!", parse_mode='HTML', reply_markup=random_prompt_keyboard())

@bot.message_handler(commands=['generate'])
def generate_command(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user and user[2]:  # Check if user exists and has a prompt set
        generate_image(message)
    else:
        bot.reply_to(message, "Oops! It seems you haven't set a prompt yet. Please set a prompt first or use /random to get a random prompt.")


@bot.message_handler(commands=['stats'])
def send_stats(message):
    if message.from_user.id == ADMIN_ID:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE prompt IS NOT NULL")
            active_users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE style IS NOT NULL")
            users_with_style = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE width IS NOT NULL AND height IS NOT NULL")
            users_with_size = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE guidance_scale IS NOT NULL")
            users_with_guidance = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE seed != -1")
            users_with_seed = cursor.fetchone()[0]
        
        stats_text = f"📊 Bot statistics:\n\n"
        stats_text += f"Total users: {user_count}\n"
        stats_text += f"Active users (with prompt): {active_users}\n"
        stats_text += f"Users with custom style: {users_with_style}\n"
        stats_text += f"Users with custom size: {users_with_size}\n"
        stats_text += f"Users with custom guidance scale: {users_with_guidance}\n"
        stats_text += f"Users with custom seed: {users_with_seed}\n"
        
        bot.reply_to(message, stats_text)
    else:
        bot.reply_to(message, "Sorry, this magical power is reserved for the administrators.")


@bot.message_handler(commands=['broadcast'])
def start_broadcast(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "What message would you like to share with all our creative minds? You can also send an image with a caption.")
        bot.register_next_step_handler(message, do_broadcast)
    else:
        bot.reply_to(message, "Sorry, the power of mass communication is for administrators only.")

# Text message handler
@bot.message_handler(func=lambda message: True)
@check_user
def handle_message(message):
    if message.text.startswith('/'):
        handle_commands(message)
    else:
        user_id = message.from_user.id
        update_user_data(user_id, 'prompt', message.text)
        reply_markup = InlineKeyboardMarkup()
        reply_markup.row(InlineKeyboardButton("Use default", callback_data="use_default_negative"))
        reply_markup.row(InlineKeyboardButton("Add custom", callback_data="add_custom_negative"))
        bot.reply_to(message, "Great prompt! Now, would you like to use the default negative prompt or add your own creative twist?", 
                     reply_markup=reply_markup)

# Inline button handler
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    logger.info(f"User {user_id} clicked button: {call.data}")
    if call.data == "create_image":
        generate_image(call.message)
    elif call.data == "settings":
        show_user_settings(call.message)
    elif call.data == "help":
        send_help(call.message)
    elif call.data == "main_menu":
        bot.edit_message_text("What would you like to do next?", call.message.chat.id, call.message.message_id, reply_markup=main_menu_keyboard())
    elif call.data == "settings":
        bot.edit_message_text("Let's customize your creation! What would you like to adjust?", call.message.chat.id, call.message.message_id, reply_markup=settings_keyboard())
    elif call.data.startswith("set_"):
        handle_setting(call)
    elif call.data.startswith("style_"):
        style = call.data.split("_", 1)[1]
        update_user_data(user_id, 'style', style)
        bot.answer_callback_query(call.id, f"Great choice! Style set to: {style}")
        bot.edit_message_text("Your style is set! What else would you like to adjust?", call.message.chat.id, call.message.message_id, reply_markup=settings_keyboard())
    elif call.data == "use_default_negative":
        update_user_data(user_id, 'negative_prompt', DEFAULT_NEGATIVE_PROMPT)
        generate_image(call.message)
    elif call.data == "add_custom_negative":
        bot.edit_message_text("Alright, creative genius! What would you like to avoid in your image? (e.g., 'blurry, low quality, distorted')", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_custom_negative)
    elif call.data == "random_prompt" or call.data == "another_random":
        prompt = generate_random_prompt()
        update_user_data(call.from_user.id, 'prompt', prompt)
        bot.edit_message_text(f"Here's a fresh spark of inspiration:\n\n<code>{prompt}</code>\n\nFeel free to use it as is or add your own flair!", call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=random_prompt_keyboard())
    elif call.data == "generate_random":
        user_id = call.from_user.id
        user = get_user(user_id)
        if user:
            prompt = user[2]  # Get the saved prompt
            reply_markup = InlineKeyboardMarkup()
            reply_markup.row(InlineKeyboardButton("Use default", callback_data="use_default_negative_random"))
            reply_markup.row(InlineKeyboardButton("Add custom", callback_data="add_custom_negative_random"))
            bot.edit_message_text("Exciting! Now, for the negative prompt: stick with the default or add your personal touch?", 
                                call.message.chat.id, call.message.message_id, reply_markup=reply_markup)
        else:
            bot.answer_callback_query(call.id, "Oops! Let's start from the beginning. Use /start to kick things off!")
    elif call.data == "use_default_negative_random":
        update_user_data(call.from_user.id, 'negative_prompt', DEFAULT_NEGATIVE_PROMPT)
        generate_image(call.message)
    elif call.data == "add_custom_negative_random":
        bot.edit_message_text("Alright, creative genius! What would you like to avoid in your image? (e.g., 'blurry, low quality, distorted')", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, process_custom_negative)
    elif call.data == "retry_generation":
        generate_image(call.message)
    
    bot.answer_callback_query(call.id)

def process_custom_negative(message):
    if message.text.startswith('/'):
        handle_commands(message)
    else:
        user_id = message.from_user.id
        custom_negative = message.text
        full_negative = f"{DEFAULT_NEGATIVE_PROMPT}, {custom_negative}"
        update_user_data(user_id, 'negative_prompt', full_negative)
        generate_image(message)

def handle_setting(call):
    setting = call.data.split("_")[1]
    if setting == "style":
        bot.edit_message_text("What style speaks to you today?", call.message.chat.id, call.message.message_id, reply_markup=style_keyboard())
    elif setting == "size":
        bot.edit_message_text(
            f"Let's set the canvas size! Enter two numbers for width and height, like this:\n\n"
            f"1024 1024 (perfect square)\n"
            f"1280 720 (widescreen)\n"
            f"{MAX_WIDTH} {MAX_HEIGHT} (maximum size)\n\n"
            f"Remember, bigger isn't always better - it affects generation time too! "
            f"What dimensions inspire you?",
            call.message.chat.id, call.message.message_id
        )
        bot.register_next_step_handler(call.message, process_size_input)
    elif setting == "guidance":
        bot.edit_message_text(
            "Time to set the Guidance Scale! This determines how closely the image follows your prompt.\n\n"
            "1-5: More creative, but might stray from your prompt\n"
            "6-10: A balanced approach\n"
            "11-20: Strictly follows the prompt, but might be less creative\n\n"
            "What's your preference? Enter a number between 1 and 20.",
            call.message.chat.id, call.message.message_id
        )
        bot.register_next_step_handler(call.message, process_guidance_input)
    elif setting == "seed":
        bot.edit_message_text(
            f"Let's talk about seeds! A seed is like a magic number that ensures consistency:\n\n"
            f"0-{MAX_SEED}: Choose any number in this range for reproducible results\n"
            f"-1: Let fate decide (random seed each time)\n\n"
            f"What's your lucky number? Or type -1 if you're feeling adventurous!",
            call.message.chat.id, call.message.message_id
        )
        bot.register_next_step_handler(call.message, process_seed_input)

def process_size_input(message):
    if message.text.startswith('/'):
        handle_commands(message)
    else:
        try:
            size = message.text.lower().replace('x', ' ').replace('*', ' ')
            width, height = map(int, size.split())
            width = min(width, MAX_WIDTH)
            height = min(height, MAX_HEIGHT)
            update_user_data(message.from_user.id, 'width', width)
            update_user_data(message.from_user.id, 'height', height)
            bot.reply_to(message, f"Perfect! Your canvas is set to {width}x{height}. Ready to create some art?", reply_markup=settings_keyboard())
        except:
            bot.reply_to(message, f"Oops! That didn't quite work. Remember, just type two numbers like '1024 1024'. Let's try again!", reply_markup=settings_keyboard())

def process_guidance_input(message):
    if message.text.startswith('/'):
        handle_commands(message)
    else:
        try:
            guidance = float(message.text)
            guidance = max(1, min(20, guidance))
            update_user_data(message.from_user.id, 'guidance_scale', guidance)
            if guidance <= 5:
                response = f"Guidance Scale set to {guidance}. We're going for creative and unexpected results!"
            elif guidance <= 10:
                response = f"Guidance Scale set to {guidance}. A perfect balance between creativity and precision."
            else:
                response = f"Guidance Scale set to {guidance}. We're aiming for high precision and close adherence to your prompt."
            bot.reply_to(message, response, reply_markup=settings_keyboard())
        except:
            bot.reply_to(message, "Hmm, that doesn't look like a number between 1 and 20. Want to give it another shot?", reply_markup=settings_keyboard())

def process_seed_input(message):
    if message.text.startswith('/'):
        handle_commands(message)
    else:
        try:
            seed = int(message.text)
            if seed == -1:
                update_user_data(message.from_user.id, 'seed', seed)
                bot.reply_to(message, "Excellent! We'll use a random seed each time. Every generation will be a surprise!", reply_markup=settings_keyboard())
            else:
                seed = max(0, min(MAX_SEED, seed))
                update_user_data(message.from_user.id, 'seed', seed)
                bot.reply_to(message, f"Great! We've locked in seed {seed}. You can use this same seed to recreate this image later if you like it.", reply_markup=settings_keyboard())
        except:
            bot.reply_to(message, f"Oops! That doesn't look like a whole number. Remember, you can use any number from 0 to {MAX_SEED}, or -1 for a random seed each time. Want to try again?", reply_markup=settings_keyboard())

def show_user_settings(message):
    user_id = message.chat.id
    user = get_user(user_id)
    if user:
        user_id, username, prompt, negative_prompt, style, width, height, guidance_scale, seed = user
        settings_text = "🎨 Your Creative Palette 🎨\n\n"
        settings_text += f"🖼 Current Prompt: {prompt or 'Not set yet'}\n\n"
        settings_text += f"🚫 Negative Prompt: {negative_prompt or 'Using default'}\n\n"
        settings_text += f"✨ Style: {style or 'Not set'}\n"
        settings_text += f"📐 Canvas Size: {width or '?'}x{height or '?'}\n"
        settings_text += f"🧭 Guidance Scale: {guidance_scale or 'Not set'}\n"
        settings_text += f"🌱 Seed: {seed if seed != -1 else 'Random'}\n\n"
        settings_text += "Ready to tweak your masterpiece? Click a button below!"
        bot.send_message(message.chat.id, settings_text, reply_markup=settings_keyboard())
    else:
        bot.reply_to(message, "Oops! It seems we haven't set up your creative space yet. Let's start with /start and make some art!")

def generate_image(message):
    user_id = message.chat.id
    user = get_user(user_id)
    if user:
        user_id, username, prompt, negative_prompt, style, width, height, guidance_scale, seed = user

        if not all([prompt, style, width, height, guidance_scale]):
            bot.reply_to(message, "Looks like we're missing some key ingredients for your masterpiece. Let's check your settings and make sure everything's in place! Have you written a prompt? :D")
            return

        processing_msg = bot.reply_to(message, "🎨 Assembling your creative vision... This might take a moment, but great art is worth the wait!")

        try:
            result = dalle_client.predict(
                prompt=prompt,
                negative_prompt=negative_prompt,
                use_negative_prompt=True,
                style=style,
                seed=seed if seed != -1 else random.randint(0, MAX_SEED),
                width=width,
                height=height,
                guidance_scale=guidance_scale,
                randomize_seed=(seed == -1),
                api_name="/run"
            )

            bot.edit_message_text("🌟 Your masterpiece is ready! Unveiling it now...", chat_id=message.chat.id, message_id=processing_msg.message_id)

            actual_seed = result[1]  # Get the actual used seed
            caption = (f"🖼 Prompt: {prompt}\n\n"
                       f"🚫 Negative prompt: {negative_prompt}\n\n"
                       f"✨ Style: {style}\n"
                       f"📐 Size: {width}x{height}\n"
                       f"🧭 Guidance scale: {guidance_scale}\n"
                       f"🌱 Seed: {actual_seed}")

            # Send the caption as a separate message
            bot.send_message(message.chat.id, caption)

            for i, img in enumerate(result[0]):
                with open(img['image'], 'rb') as image_file:
                    bot.send_photo(message.chat.id, image_file)
                with open(img['image'], 'rb') as image_file:
                    bot.send_document(message.chat.id, image_file)

            logger.info(f"Generated image for user {user_id}. {caption}")

            bot.send_message(message.chat.id, "What do you think? Ready to create another masterpiece?", reply_markup=main_menu_keyboard())

        except Exception as e:
            if 'GPU task aborted' in str(e):
                error_message = "Oops! It seems our digital paintbrush ran out of ink. Let's try again in a moment!"
            else:
                error_message = f"Uh-oh! We hit a creative block:\n\n🚫 {str(e)}\n\nShall we try again or tweak our artistic vision?"
            
            retry_markup = InlineKeyboardMarkup()
            retry_markup.add(InlineKeyboardButton("Try again", callback_data="retry_generation"))
            retry_markup.add(InlineKeyboardButton("Adjust settings", callback_data="my_settings"))
            
            bot.edit_message_text(error_message, chat_id=message.chat.id, message_id=processing_msg.message_id, reply_markup=retry_markup)
            logger.error(f"Error for user {user_id}: {str(e)}")

def do_broadcast(message):
    if message.from_user.id == ADMIN_ID:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users")
            users = cursor.fetchall()
        successful = 0
        failed = 0
        for user in users:
            try:
                if message.content_type == 'text':
                    bot.send_message(user[0], message.text)
                elif message.content_type == 'photo':
                    photo = message.photo[-1]  # Get the largest photo
                    bot.send_photo(user[0], photo.file_id, caption=message.caption)
                successful += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send broadcast to user {user[0]}: {str(e)}")
        bot.reply_to(message, f"Broadcast complete!\n✅ Successfully delivered: {successful}\n❌ Undelivered: {failed}")
    else:
        bot.reply_to(message, "Sorry, the power of mass communication is for administrators only.")


# Error handling function
def handle_exception(exception):
    print(f"Oops! We encountered a hiccup: {exception}")
    # You can add error logging or send notifications to the administrator here

logger.info("The creative journey begins! Our bot is up and running.")

# Bot launch
if __name__ == "__main__":
    while True:
        try:
            initialize_database()
            bot.polling(none_stop=True, timeout=120, long_polling_timeout=140)
        except Exception as e:
            handle_exception(e)
            time.sleep(30)
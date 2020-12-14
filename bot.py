import hashlib
from urllib.request import urlopen

import telegram
from telegram.ext import Updater, MessageHandler, Filters
from telegram.ext import CommandHandler

import logging

import json
import os
from datetime import datetime as dt
from urllib.parse import urlparse

from pathlib import Path
from termcolor import colored

data_path = Path.cwd().joinpath('resources').joinpath('data.json')
kraljevo_path = Path.cwd().joinpath('resources').joinpath('kraljevo.jpg')


def print_log(text, data):
    print(colored(dt.now().strftime("%I:%M:%S %p"), 'cyan'), " ", colored(text, 'magenta'), data)


def read_hash(url):
    response = urlopen(url).read()
    current_hash = hashlib.sha224(response).hexdigest()
    return current_hash


def check_user_base(id):
    with open(data_path, 'r') as file:
        data = json.load(file)

    if id not in data:
        return False
    else:
        return True


def check_if_url_valid(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def start(update, context):
    current_chat_id = str(update.effective_chat.id)
    if check_user_base(current_chat_id) is False:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I am a bot and I will notify you "
                                                                        "whenever a site changes.\n"
                                                                        "Welcome!")
        with open(data_path, 'r') as file:
            data = json.load(file)

        current_chat_id = str(update.effective_chat.id)
        data[current_chat_id] = {}

        with open(data_path, 'w') as file:
            json.dump(data, file)

        text = 'Here\'s the list of my commands:\n' \
               '/start - Make an entry for yourself in the database\n' \
               '️/follow <link(s)> - Url(s) that you\'d like to keep track of\n' \
               '/unfollow <link(s)> - Url(s) that you no longer want to keep track of\n' \
               '/unfollow_all - Delete all your urls from database\n' \
               '️/list - Info on what you follow\n' \
               '/help - Bot manual\n' \
               '/end - Wipe all your data'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="You have already started the bot"
                                                                        " once. :)")


def end(update, context):
    current_chat_id = str(update.effective_chat.id)
    if check_user_base(current_chat_id) is True:
        context.bot.send_message(chat_id=update.effective_chat.id, text="I have wiped all your data.")

        with open(data_path, 'r') as file:
            data = json.load(file)

        current_chat_id = str(update.effective_chat.id)
        data.pop(current_chat_id)

        with open(data_path, 'w') as file:
            json.dump(data, file)

    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="You are not in the database... yet.")


def follow(update, context):
    global data_path
    current_chat_id = str(update.effective_chat.id)

    if check_user_base(current_chat_id) is False:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please /start using the bot first.\n')
        return

    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text='That command requires '
                                                                        'at least 1 argument.')
        return
    urls = context.args

    with open(data_path, 'r') as file:
        data = json.load(file)

    for url in urls:
        if not check_if_url_valid(url):
            context.bot.send_message(chat_id=update.effective_chat.id, text='Url not valid:\n'
                                                                            + url + '\n')
        elif url not in data[current_chat_id]:
            hash_code = read_hash(url)
            data[current_chat_id][url] =  hash_code
            context.bot.send_message(chat_id=update.effective_chat.id, text='Successfully followed:\n'
                                                                            + url + '\n')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='Entry already exists:\n'
                                                                            + url + '\n')

    with open(data_path, 'w') as file:
        json.dump(data, file)


def unfollow(update, context):
    global data_path
    current_chat_id = str(update.effective_chat.id)

    if check_user_base(current_chat_id) is False:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please /start using the bot first.\n')
        return

    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text='That command requires '
                                                                        'at least 1 argument.')
        return

    urls = context.args

    with open(data_path, 'r') as file:
        data = json.load(file)

    for url in urls:
        if not check_if_url_valid(url):
            context.bot.send_message(chat_id=update.effective_chat.id, text='Url not valid:\n'
                                                                            + url + '\n')
        elif url in data[current_chat_id]:
            data[current_chat_id].pop(url)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='Successfully unfollowed: ' + url + '\n')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='Url not found: ' + url + '\n')

    with open(data_path, 'w') as file:
        json.dump(data, file)


def unfollow_all(update, context):
    global data_path
    current_chat_id = str(update.effective_chat.id)

    with open(data_path, 'r') as file:
        data = json.load(file)

    if check_user_base(current_chat_id) is False:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please /start using the bot first.\n')
        return

    if data[current_chat_id] != {}:
        text = 'I have unfollowed all of your sites:\n'

        for url in data[current_chat_id]:
            text = text + '- ' + url + '\n'
        print()

        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

        data[current_chat_id] = {}
        with open(data_path, 'w') as file:
            json.dump(data, file)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='No sites to unfollow. Maybe try adding some sites first?')


def list_all(update, context):
    global data_path
    current_chat_id = str(update.effective_chat.id)

    if check_user_base(current_chat_id) is False:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Please /start using the bot first.\n')
        return

    with open(data_path, 'r') as file:
        data = json.load(file)

    if data[current_chat_id] != {}:
        text = 'These are all of the sites you follow:\n'

        for url in data[current_chat_id]:
            text = text + '- ' + url + '\n'
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=text)

    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Currently you do not follow anything.\n')


def show_help(update, context):
    text = 'Here\'s the list of my commands:\n' \
           '/start - Make an entry for yourself in the database\n' \
           '️/follow <link(s)> - Url(s) that you\'d like to keep track of\n' \
           '/unfollow <link(s)> - Url(s) that you no longer want to keep track of\n' \
           '/unfollow_all - Delete all your urls from database\n' \
           '️/list - Info on what you follow\n' \
           '/help - Bot manual\n' \
           '/end - Wipe all your data'
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def kraljevo(update, context):
    global kraljevo_path
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(kraljevo_path, 'rb'))


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command!\n")


def callback_minute(context: telegram.ext.CallbackContext):
    global data_path

    with open(data_path, 'r') as file:
        data = json.load(file)

    for chat_id in data:
        print_log("Monitoring sites for chat: ", chat_id)
        print_log("Sites: ", data[chat_id])
        print()

        for url in data[chat_id]:
            hash_code = read_hash(url)
            if hash_code != data[chat_id][url]:
                data[chat_id][url] = hash_code
                print_log("Change noted: ", url)
                print()
                text = "The content of the following site has changed:\n" + url
                context.bot.send_message(chat_id=int(chat_id), text=text)

    with open(data_path, 'w') as file:
        json.dump(data, file)


TOKEN = '1275479367:AAGNjTawDfsqhDW9M2zn3-bmZdev_LZkdow'
PORT = int(os.environ.get('PORT', '8443'))

updater = Updater(token=TOKEN, use_context=True)
job_queuer = updater.job_queue

updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
updater.bot.setWebhook('https://avro-bot.herokuapp.com/' + TOKEN)

dispatcher = updater.dispatcher

# Uncomment this if you'd like integrated logging
# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

start_handler = CommandHandler('start', start, run_async=True)
follow_handler = CommandHandler('follow', follow, run_async=True)
unfollow_handler = CommandHandler('unfollow', unfollow, run_async=True)
unfollow_all_handler = CommandHandler('unfollow_all', unfollow_all, run_async=True)
list_handler = CommandHandler('list', list_all)
help_handler = CommandHandler('help', show_help)
kraljevo_handler = CommandHandler('kraljevo', kraljevo)
end_handler = CommandHandler('end', end, run_async=True)

unknown_handler = MessageHandler(Filters.command, unknown)

dispatcher.add_handler(kraljevo_handler)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(follow_handler)
dispatcher.add_handler(unfollow_handler)
dispatcher.add_handler(unfollow_all_handler)
dispatcher.add_handler(list_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(end_handler)
dispatcher.add_handler(unknown_handler)

job_queuer.run_repeating(callback_minute, interval=30, first=0)

updater.start_polling()
updater.idle()
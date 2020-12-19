import telegram
from telegram.ext import Updater, MessageHandler, Filters
from telegram.ext import CommandHandler

# Uncomment if you're using built-in logging.
#import logging

import hashlib
import requests
import os
import psycopg2 as pscg
from datetime import datetime as dt
from urllib.request import Request, urlopen
from pathlib import Path
from termcolor import colored


kraljevo_path = Path.cwd().joinpath('resources').joinpath('kraljevo.jpg')

# Credentials for database connection stored in system variable.
# Visit https://www3.ntu.edu.sg/home/ehchua/programming/howto/Environment_Variables.html for more info.
DATABASE_URL = os.environ['DATABASE_URL']
CREATOR_ID = os.environ['CREATOR_ID']


# Custom console logging.
def print_log(text, data = ""):
    print(colored(dt.now().strftime("%I:%M:%S %p"), 'cyan'), " ", colored(text, 'magenta'), data)


# Bypass anti-crawler systems by using browser's "identity".
# Reads an url content and returns a hash value.
def get_url_hash(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urlopen(req).read()
    current_hash = hashlib.sha224(response).hexdigest()
    return current_hash


def is_url_valid(url):
    try:
        requests.get(url)
        return True
    except Exception:
        return False


def is_url_valid_length(url):
    if len(url) < 1500:
        return True
    else:
        return False


def start(update, context):
    current_chat_id = update.effective_chat.id

    context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I am a bot and I will notify you "
                                                                    "whenever a site changes.\n"
                                                                    "Welcome!\n\nYour chat id is: "
                                                                    + str(current_chat_id))

    text = "Here\'s the list of my commands:\n\n" \
            "/start - See the starting message\n" \
            "/follow <link(s)> - Url(s) that you\'d like to keep track of\n" \
            "/unfollow <link(s)> - Url(s) that you no longer want to keep track of\n" \
            "/unfollow_all - Delete all your urls from database\n" \
            "/list - Info on what you follow\n" \
            "/help - Bot manual\n" \
            "/comment <comment> - Leave a comment for me! For safety reasons, max 30 comments per user is permitted\n" \
            "/list_comments - See all your comments\n" \
            "/end - Wipe all your data\n"

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def end(update, context):
    current_chat_id = update.effective_chat.id
    cursor = None
    conn = None

    # DB connection
    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        cursor = conn.cursor()
        delete_query1 = "delete from public.user_data where chat_id = %s"
        delete_query2 = "delete from public.user_comments where chat_id = %s"

        try:
            cursor.execute(delete_query1, [current_chat_id])
            conn.commit()
            context.bot.send_message(chat_id=update.effective_chat.id, text="Url data wiped.")

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to "
                                                                            "wipe url data.")
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", delete_query1)
            print_log("Chat_id: ", current_chat_id)
            print_log("Fail message: ", e.pgerror)
            print()

        try:
            cursor.execute(delete_query2, [current_chat_id])
            conn.commit()
            context.bot.send_message(chat_id=update.effective_chat.id, text="Comments data wiped.")

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to "
                                                                            "wipe comments data.")
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", delete_query2)
            print_log("Chat_id: ", current_chat_id)
            print_log("Fail message: ", e.pgerror)
            print()


    except pscg.Error as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


def follow(update, context):
    current_chat_id = update.effective_chat.id
    print_log("Follow command invoked for chat_id: ", str(current_chat_id))

    # There should be at least 1 url sent together with command
    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="That command requires "
                                                                        "at least 1 argument.")
        return

    urls = context.args
    conn = None
    cursor = None

    for url in urls:
        # Check if url is in valid format and if it exists
        if not is_url_valid(url):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Url not valid:\n" + url + "\n")
            continue

        # Check the length of url (1500 is upper max defined in database)
        if not is_url_valid_length(url):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Url must be less than 1500 characters:\n"
                                                                            + url + "\n")
            continue

        # DB connection
        try:
            conn = pscg.connect(DATABASE_URL, sslmode='require')
            print_log("Successfully connected to database!")

            cursor = conn.cursor()

            check_query = "select *  from public.user_data where chat_id = %s and url = %s"

            # Check if the entry already exists
            try:
                cursor.execute(check_query, (current_chat_id, url))
                conn.commit()

                # Add if not
                if cursor.fetchone() is None:
                    insert_query = "insert into public.user_data (chat_id, url, hash) values (%s, %s, %s)"
                    values = (current_chat_id, url, get_url_hash(url))

                    try:
                        cursor.execute(insert_query, values)
                        conn.commit()
                        context.bot.send_message(chat_id=update.effective_chat.id, text="Successfully followed:\n"
                                                                                        + url)
                        print_log(str(current_chat_id) + ": followed ", url)
                    except pscg.Error as e:
                        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed "
                                                                                        "to make an entry for url:\n"
                                                                                        + url)
                        print()
                        print_log(e.pgcode, ": Failed to execute query.")
                        print_log("Query in question: ", insert_query)
                        print_log("Chat_id: ", current_chat_id)
                        print_log("Fail message: ", e.pgerror)
                        print()

                # Send a message if it does
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Entry already exists:\n"
                                                                                    + url)
                    print_log(str(current_chat_id) + ": entry already exists ", url)

            except pscg.Error as e:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed "
                                                                                "to check if there's an entry:\n"
                                                                                + url)
                print()
                print_log(e.pgcode, ": Failed to execute query.")
                print_log("Query in question: ", check_query)
                print_log("Chat_id: ", current_chat_id)
                print_log("Fail message: ", e.pgerror)
                print()

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
            print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
            print_log("Fail message: ", e.pgerror)
        finally:
            if conn:
                cursor.close()
                conn.close()
                print_log("PostgreSQL connection is closed.")


def unfollow(update, context):
    current_chat_id = update.effective_chat.id

    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text='That command requires '
                                                                        'at least 1 argument.')
        return

    urls = context.args
    conn = None
    cursor = None

    for url in urls:
        # Check if url is in valid format and if it exists
        if not is_url_valid(url):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Url not valid:\n" + url + "\n")
            continue

        # Check the length of url (1500 is upper max defined in database)
        if not is_url_valid_length(url):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Url must be less than 1500 characters:\n"
                                                                            + url + "\n")
            continue

        # DB connection
        try:
            conn = pscg.connect(DATABASE_URL, sslmode='require')
            print_log("Successfully connected to database!")

            cursor = conn.cursor()

            check_query = "select *  from public.user_data where chat_id = %s and url = %s"

            # Check if the entry already exists
            try:
                cursor.execute(check_query, (current_chat_id, url))
                conn.commit()

                # Delete if yes
                if cursor.fetchone() is not None:
                    delete_query = "delete from public.user_data where chat_id = %s and url = %s"
                    values = (current_chat_id, url)

                    try:
                        cursor.execute(delete_query, values)
                        conn.commit()
                        context.bot.send_message(chat_id=update.effective_chat.id, text="Successfully unfollowed:\n"
                                                                                        + url)
                        print_log(str(current_chat_id) + ": unfollowed ", url)
                    except pscg.Error as e:
                        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed "
                                                                                        "to delete an entry for url:\n"
                                                                                        + url)
                        print()
                        print_log(e.pgcode, ": Failed to execute query.")
                        print_log("Query in question: ", delete_query)
                        print_log("Chat_id: ", current_chat_id)
                        print_log("Fail message: ", e.pgerror)
                        print()

                # Send a message if it does not
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Entry does not exist:\n"
                                                                                    + url)
                    print_log(str(current_chat_id) + ": entry does not exist ", url)

            except pscg.Error as e:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed "
                                                                                "to check if there's an entry:\n"
                                                                                + url)
                print()
                print_log(e.pgcode, ": Failed to execute query.")
                print_log("Query in question: ", check_query)
                print_log("Chat_id: ", current_chat_id)
                print_log("Fail message: ", e.pgerror)
                print()

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
            print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
            print_log("Fail message: ", e.pgerror)
        finally:
            if conn:
                cursor.close()
                conn.close()
                print_log("PostgreSQL connection is closed.")


def unfollow_all(update, context):
    current_chat_id = update.effective_chat.id

    conn = None
    cursor = None

    # DB connection
    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        cursor = conn.cursor()

        delete_query = "delete from public.user_data where chat_id = %s"

        try:
            cursor.execute(delete_query, [current_chat_id])
            conn.commit()
            context.bot.send_message(chat_id=update.effective_chat.id, text="Your list of urls is now empty.")

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to "
                                                                            "delete your data.")
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", delete_query)
            print_log("Chat_id: ", current_chat_id)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


def list_all(update, context):
    current_chat_id = update.effective_chat.id
    cursor = None
    conn = None

    # DB connection
    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        # Selecting all urls from current users and reporting
        cursor = conn.cursor()
        lookup_query = "select url from public.user_data where chat_id = %s"

        try:
            cursor.execute(lookup_query, [current_chat_id])
            data = cursor.fetchall()

            if data:
                text = "Urls you follow:\n"

                for url in data:
                    url_txt = str(url[0])
                    text = text + "- " + url_txt + "\n"

                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Currently you do not follow "
                                                                                "anything.")

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to "
                                                                            "list your data.")
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", lookup_query)
            print_log("Chat_id: ", current_chat_id)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


def show_help(update, context):
    text = "Here\'s the list of my commands:\n\n" \
           "/start - See the starting message\n" \
           "/follow <link(s)> - Url(s) that you\'d like to keep track of\n" \
           "/unfollow <link(s)> - Url(s) that you no longer want to keep track of\n" \
           "/unfollow_all - Delete all your urls from database\n" \
           "/list - Info on what you follow\n" \
           "/help - Bot manual\n" \
           "/comment <comment> - Leave a comment for me! For safety reasons, max 30 comments per user is permitted\n" \
           "/list_comments - See all your comments\n" \
           "/end - Wipe all your data\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def comment(update, context):
    current_chat_id = update.effective_chat.id
    conn = None
    cursor = None

    # If text of comment is empty no point in sending anything
    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text='That command requires '
                                                                        'at least 1 argument.')
        return

    # Send creator a message; creator chat id is a system variable
    comment_text = " ".join(context.args)
    context.bot.send_message(chat_id=CREATOR_ID, text="New comment arrived:\n\n" + comment_text)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Successfully sent a comment to the creator.")

    # If user did not flood the database, make an entry for his comment,
    # and if possible, update the name and username
    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        cursor = conn.cursor()
        check_query = "select * from public.user_comments where chat_id = %s"

        try:
            cursor.execute(check_query, [current_chat_id])
            conn.commit()
            data = cursor.fetchall()

            if len(data) < 30:
                insert_query = "insert into public.user_comments (chat_id, comment_text) values (%s, %s)"
                values = [current_chat_id, comment_text]

                try:
                    cursor.execute(insert_query, values)
                    conn.commit()
                    print_log(str(current_chat_id) + ": User sent a comment.")

                    username_query = "update public.user_comments set username = %s " \
                                     "where chat_id = %s and comment_text = %s"
                    name_query = "update public.user_comments set first_name = %s " \
                                 "where chat_id = %s and comment_text = %s"

                    username = update.effective_chat.username
                    name = update.effective_chat.first_name

                    if username:
                        try:
                            cursor.execute(username_query, [username, current_chat_id, comment_text])
                            conn.commit()
                            print_log(str(current_chat_id) + ": Username updated.")
                        except pscg.Error as e:
                            print()
                            print_log(e.pgcode, ": Failed to execute query.")
                            print_log("Query in question: ", username_query)
                            print_log("Chat_id: ", current_chat_id)
                            print_log("Fail message: ", e.pgerror)
                            print()

                    if name:
                        try:
                            cursor.execute(name_query, [name, current_chat_id, comment_text])
                            conn.commit()
                            print_log(str(current_chat_id) + ": Name updated.")
                        except pscg.Error as e:
                            print()
                            print_log(e.pgcode, ": Failed to execute query.")
                            print_log("Query in question: ", name_query)
                            print_log("Chat_id: ", current_chat_id)
                            print_log("Fail message: ", e.pgerror)
                            print()

                except pscg.Error as e:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed "
                                                                                    "to save a comment... "
                                                                                    "But the creator still got "
                                                                                    "it as a message, don't worry.\n")
                    print()
                    print_log(e.pgcode, ": Failed to execute query.")
                    print_log("Query in question: ", insert_query)
                    print_log("Chat_id: ", current_chat_id)
                    print_log("Fail message: ", e.pgerror)
                    print()

            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="You've sent too many comments "
                                                                                "already... Wait for the "
                                                                                "automatic cleanup, it might take a "
                                                                                "few days.")
                print_log(str(current_chat_id) + ": user maximized number of comments.")

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed "
                                                                            "to do a checkup...")
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", check_query)
            print_log("Chat_id: ", current_chat_id)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


def list_comments(update, context):
    current_chat_id = update.effective_chat.id
    cursor = None
    conn = None

    # DB connection
    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        # Selecting all urls from current users and reporting
        cursor = conn.cursor()
        lookup_query = "select comment_id, comment_text from public.user_comments where chat_id = %s"

        try:
            cursor.execute(lookup_query, [current_chat_id])
            data = cursor.fetchall()

            if data:
                text = "Your comments:\n\n-----\n"

                for comment_id, comment_text in data:
                    text = text + "Comment id: " + str(comment_id) + "\n" +\
                           "Comment text:\n" + str(comment_text) + "\n-----\n"

                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="You've got no comments.")

        except pscg.Error as e:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to "
                                                                            "list your data.")
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", lookup_query)
            print_log("Chat_id: ", current_chat_id)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")
            

def kraljevo(update, context):
    global kraljevo_path
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(kraljevo_path, 'rb'))


def send_a_message_to_users(update, context):
    sender_chat_id = chat_id=update.effective_chat.id
    cursor = None
    conn = None

    if sender_chat_id != CREATOR_ID:
        context.bot.send_message(chat_id=update.effective_chat.id, text='You are not allowed to use that command. :)')
        return

    # Message has to have a text
    if len(context.args) < 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text='That command requires '
                                                                        'at least 1 argument.')
        return

    # Send creator a message; creator chat id is a system variable
    message_text = context.args.join(" ")

    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        # Selecting all chat ids from database
        cursor = conn.cursor()
        lookup_query = "select distinct chat_id from public.user_data"

        try:
            cursor.execute(lookup_query)
            conn.commit()
            data = cursor.fetchall()

            if data:
                for chat_id in data:
                    if chat_id != CREATOR_ID:
                        print_log("Sending a message to: ", chat_id)
                        context.bot.send_message(chat_id=chat_id, text=message_text)

        except pscg.Error as e:
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", lookup_query)
            print_log("Chat_id: ", chat_id)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Unknown command!\n")


def callback_minute(context: telegram.ext.CallbackContext):
    cursor = None
    conn = None

    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        # Selecting all urls from current users and report if hash has changed
        # since the last callback
        cursor = conn.cursor()
        lookup_query = "select chat_id, url, hash from public.user_data"

        try:
            cursor.execute(lookup_query)
            conn.commit()
            data = cursor.fetchall()

            update_query = "update public.user_Data set hash = %s where chat_id = %s and url = %s"

            if data:
                for chat_id, url, hash_code in data:
                    print_log("Monitoring url for chat: ", chat_id)
                    print_log("url: ", url)

                    hash_new = get_url_hash(url)
                    if hash_code != hash_new:
                        try:
                            cursor.execute(update_query, [hash_new, chat_id, url])
                            conn.commit()
                            print_log("Change noted for user %s: " % str(chat_id), url)
                            text = "The content of the following site has changed:\n" + url
                            context.bot.send_message(chat_id=chat_id, text=text)
                        except pscg.Error as e:
                            print()
                            print_log(e.pgcode, ": Failed to execute query.")
                            print_log("Query in question: ", update_query)
                            print_log("Chat_id: ", chat_id)
                            print_log("Fail message: ", e.pgerror)
                            print()

        except pscg.Error as e:
            print()
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", lookup_query)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        context.bot.send_message(chat_id=CREATOR_ID, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


def callback_10_days(context: telegram.ext.CallbackContext):
    cursor = None
    conn = None

    try:
        conn = pscg.connect(DATABASE_URL, sslmode='require')
        print_log("Successfully connected to database!")

        # Delete all comments
        cursor = conn.cursor()
        refresh_query = "delete from public.user_comments"

        try:
            cursor.execute(refresh_query)
            conn.commit()
            context.bot.send_message(chat_id=CREATOR_ID, text="I have refreshed the comments database.")
            print_log("Comments database refreshed.")

        except pscg.Error as e:
            print()
            context.bot.send_message(chat_id=CREATOR_ID, text="Failed to refresh the comments database...")
            print_log(e.pgcode, ": Failed to execute query.")
            print_log("Query in question: ", refresh_query)
            print_log("Fail message: ", e.pgerror)
            print()

    except pscg.Error as e:
        context.bot.send_message(chat_id=CREATOR_ID, text="Database issues. Failed to connect...:\n")
        print_log("Failed to connect to PostgreSQL database: ", e.pgcode)
        print_log("Fail message: ", e.pgerror)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print_log("PostgreSQL connection is closed.")


TOKEN = os.environ['TOKEN']
PORT = int(os.environ.get('PORT', '8443'))

updater = Updater(token=TOKEN, use_context=True)
job_queuer = updater.job_queue

# updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
# updater.bot.setWebhook('https://avro-bot.herokuapp.com/' + TOKEN)

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
comment_handler = CommandHandler('comment', comment)
list_comments_handler = CommandHandler('list_comments', list_comments)
send_a_message_to_users_handler = CommandHandler('send_a_message_to_users', send_a_message_to_users)
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
dispatcher.add_handler(comment_handler)
dispatcher.add_handler(list_comments_handler)
dispatcher.add_handler(send_a_message_to_users_handler)
dispatcher.add_handler(unknown_handler)

job_queuer.run_repeating(callback_minute, interval=30, first=0)
job_queuer.run_repeating(callback_10_days, interval=432000, first=432000)

updater.start_polling()
updater.idle()
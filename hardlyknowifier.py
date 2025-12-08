import json
import sys
import os
import random
import time
import re
from datetime import datetime
from http.client import HTTPSConnection

CONFIG_FILE = "config.txt"
IGNORED_FILE = "ignored.txt"
TRIGGERS_FILE = "triggers.txt"

BLACKLIST = [
    re.compile(r"n(?:[^a-z0-9\s]*[i1!\|]){1}(?:[^a-z0-9\s]*[g6bq9G]){2}(?:[^a-z0-9\s]*[e3a@r])?(?:[^a-z0-9\s]*[r|a|ah|uh])?", re.IGNORECASE),
    re.compile(r"\bf\W*[a@4e3]\W*[gq96]\W*a?r?s?\b",re.IGNORECASE),
    re.compile(r"\bf(?:[^a-z0-9\s]*[a@4e3]){1}(?:[^a-z0-9\s]*[gq96]){1}(?:[^a-z0-9\s]*[a@4])?(?:[^a-z0-9\s]*[r]?)\b", re.IGNORECASE),
    re.compile(r"\bt\s*r\s*a\s*n\s*n\s*y\b", re.IGNORECASE)
]


def get_timestamp():
    return "[" + datetime.now().strftime("%H:%M:%S") + "]"


def read_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            token = lines[0].strip()
            channel = lines[1].strip()
            ignore_self = lines[2].strip().lower() == "true"
            return token, channel, ignore_self
    except Exception as error:
        if not isinstance(error, FileNotFoundError):
            print(f"{get_timestamp()} Error reading config: {error}")
    return None, None, None


def write_config(token, channel_id, ignore_self):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            file.write(token + "\n" + channel_id + "\n" + str(ignore_self))
    except Exception as error:
        print(f"{get_timestamp()} Error writing config: {error}")
        input("Press Enter to exit...")
        sys.exit()


def configure():
    try:
        token = input("Discord token: ")
        channel = input("Discord channel ID: ")
        ignore_self = input("Ignore your own messages? (y/n): ").strip().lower() == "y"
        write_config(token, channel, ignore_self)
        print("Written config to config.txt. Continuing with new configuration...")
        return token, channel, ignore_self
    except Exception as error:
        print(f"{get_timestamp()} Error configuring: {error}")
        input("Press Enter to exit...")
        sys.exit()


def get_connection():
    return HTTPSConnection("discord.com", 443)


def get_last_message(token, channel_id):
    try:
        headers = {"authorization": token, "host": "discord.com"}
        connectionection = get_connection()
        connectionection.request("GET", f"/api/v9/channels/{channel_id}/messages?limit=1", headers=headers)
        response = connectionection.getresponse()
        data = response.read().decode()
        connectionection.close()
    except Exception as error:
        print(f"{get_timestamp()} Network error getting messages: {error}")
        return None

    if not data:
        return None

    try:
        if response.status != 200:
            print(f"{get_timestamp()} Failed fetching messages ({response.status}): {data}")
            return None
        array = json.loads(data)
        return array[0] if array else None
    except Exception as error:
        print(f"{get_timestamp()} Error parsing message response: {error}")
        return None


def send_message(token, channel_id, content):
    payload = json.dumps({"content": content})
    headers = {"content-type": "application/json", "authorization": token, "host": "discord.com"}

    while True:
        try:
            connectionection = get_connection()
            connectionection.request("POST", f"/api/v9/channels/{channel_id}/messages", payload, headers)
            response = connectionection.getresponse()
            body = response.read().decode()
            connectionection.close()
        except Exception as error:
            print(f"{get_timestamp()} Network error sending message: {error}")
            return False

        if response.status == 429:
            try:
                retry_after = json.loads(body).get("retry_after", 1)
            except Exception:
                retry_after = 1
            print(f"{get_timestamp()} Rate-limited. Retrying in {retry_after}s")
            time.sleep(retry_after + 0.05)
            continue

        if 199 < response.status < 300:
            print(f"{get_timestamp()} Sent: {content}")
            return True

        print(f"{get_timestamp()} Failed to send ({response.status}): {body}")
        return False


def set_channel():
    config = read_config()
    if config:
        token = config[0]
        channel = input("Discord channel ID: ")
        _, _, ignore_self = read_config()
        write_config(token, channel, ignore_self)
        print("Written config to config.txt, please rerun to start!")


def show_help():
    print("Usage:")
    print("  'python hardlyknowifier.py'               :  Runs the bot. Sit back and watch pure comedy gold.")
    print("  'python hardlyknowifier.py --config'      :  Configure settings.")
    print("  'python hardlyknowifier.py --channel'     :  Set channel to send messages to.")
    print("  'python hardlyknowifier.py --help'        :  Show help (You just did that lol).")


def load_list_file(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                return {line.strip().lower() for line in file if line.strip()}
        except Exception as error:
            print(f"{get_timestamp()} Error loading {filename}: {error}")
    return set()


def check_blacklist(word):
    for pattern in BLACKLIST:
        if pattern.search(word):
            return True
    return False


def get_arguments():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--config":
            configure()
            return
        elif sys.argv[1] == "--channel":
            set_channel()
            return
        elif sys.argv[1] == "--help":
            show_help()
            return


def main():
    token, channel, ignore_self = read_config()
    if not token or not channel:
        print(f"{get_timestamp()} No config was found. Running configuration setup.")
        token, channel, ignore_self = configure()

    ignored = load_list_file(IGNORED_FILE)
    triggers = load_list_file(TRIGGERS_FILE)
    if not triggers:
        triggers = {"er"}

    print(f"{get_timestamp()} Checking latest messages.\nTriggers: {triggers}, Ignored: {ignored}\n\n")

    last_timestamp = None
    my_user_id = None

    while True:
        message = get_last_message(token, channel)
        if not message:
            time.sleep(1 + random.uniform(0.05, 0.25))
            continue

        message_timestamp = message.get("id")
        
        content = message.get("content") or ""
        author = message.get("author", {}).get("id")

        if message_timestamp == last_timestamp:
            time.sleep(1 + random.uniform(0.05, 0.25))
            continue
        last_timestamp = message_timestamp

        # get own user id, used for ignoring own messages
        if my_user_id is None:
            try:
                connection = get_connection()
                connection.request("GET", "/api/v9/users/@me", headers={"authorization": token})
                responce = connection.getresponse()
                data = responce.read().decode()
                connection.close()
                if responce.status == 200:
                    me = json.loads(data)
                    my_user_id = me.get("id")
                else:
                    print(f"{get_timestamp()} Failed to fetch @me ({responce.status}): {data}")
            except Exception as error:
                print(f"{get_timestamp()} Error fetching @me: {error}")

        # Ignore own messages if configured
        if ignore_self and author == my_user_id:
            print(f"{get_timestamp()} Found message by self, skipping.")
            time.sleep(1)
            continue

        # Avoid replying to bot message
        if "i hardly know 'er!" in content.lower():
            continue

        words = re.findall(r"\b\w+\b", content)
        replied = False
        skip_reasons = ""

        for word in words:
            word = word.lower()
            if word.endswith("s") and len(word) > 1:
                word = word[:-1]

            if check_blacklist(word):
                skip_reasons += f"'{word}' is blacklisted. "
                continue
            
            if word in ignored:
                skip_reasons += f"'{word}' is in ignored.txt. "
                continue

            for trigger in triggers:
                trigger = trigger.lower()

                if not word.endswith(trigger):
                    continue

                if len(word) <= len(trigger) + 1:
                    skip_reasons += f"'{word}' is too short. "
                    continue
                
                if len(word) - len(trigger) > 20:
                    skip_reasons += f"'{word}' is too long. "
                    continue

                if word[-len(trigger)-1] in "aeiou":
                    skip_reasons += f"'{word}' has a vowel before '{trigger}'. "
                    continue

                if any(character.isdigit() for character in word):
                    skip_reasons += f"'{word}' contains numbers. "
                    continue
                
                if re.search(r"(.)\1{2,}", word):
                    skip_reasons += f"'{word}' has too many repeated letters in a row. "
                    continue

                
                vowel_streak = 0
                consonant_streak = 0
                has_five_vowels = False
                has_five_consonants = False
                for character in word.lower():
                    if character.isalpha():
                        if character in "aeiou":
                            vowel_streak += 1
                            consonant_streak = 0
                        else:
                            consonant_streak += 1
                            vowel_streak = 0
                    else:
                        vowel_streak = 0
                        consonant_streak = 0

                    if vowel_streak >= 5:
                        has_five_vowels = True
                    if consonant_streak >= 5:
                        has_five_consonants = True

                if has_five_vowels:
                    skip_reasons += f"'{word}' has 5 consecutive vowels. "
                    continue

                if has_five_consonants:
                    skip_reasons += f"'{word}' has 5 consecutive consonants. "
                    continue


                print(f"{get_timestamp()} Found message with trigger '{trigger}', replying.")
                reply_text = f"{word.capitalize()}? I hardly know 'er!"
                sent_ok = send_message(token, channel, reply_text)
                if sent_ok:
                    replied = True
                else:
                    print(f"{get_timestamp()} Failed to send reply for: {word}")
                break 

        if not replied:
            if skip_reasons != "":
                print(f"{get_timestamp()} Found message didn't pass checks, skipping. {skip_reasons}")
            else:
                print(f"{get_timestamp()} Found message has no trigger, skipping.")

        time.sleep(0.5 + random.uniform(0.05, 0.25))


if __name__ == "__main__":
    main()

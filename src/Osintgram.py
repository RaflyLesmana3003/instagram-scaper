from ast import If
import datetime
from itertools import count
import json
import random
import sys
import urllib
import os
import codecs
from pathlib import Path
import csv
import requests
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import names
from random_word import RandomWords
import time
from geopy.geocoders import Nominatim
from instagram_private_api import Client as AppClient
from instagram_private_api import ClientCookieExpiredError, ClientLoginRequiredError, ClientError, ClientThrottledError
from prettytable import PrettyTable
from src import printcolors as pc
from src import config
from instagrapi import Client


class Osintgram:
    api = None
    api2 = None
    geolocator = Nominatim(user_agent="http")
    user_id = None
    target_id = None
    is_private = True
    following = False
    target = ""
    writeFile = False
    jsonDump = False
    cli_mode = False
    output_dir = "output"


    def __init__(self, target, is_file, is_json, is_cli, output_dir, clear_cookies):
        self.output_dir = output_dir or self.output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        u = config.getUsername()
        p = config.getPassword()
        self.clear_cookies(clear_cookies)
        self.cli_mode = is_cli
        if not is_cli:
          print("\nAttempt to login...")
        self.login(u, p)
        self.setTarget(target)
        self.writeFile = is_file
        self.jsonDump = is_json

    def clear_cookies(self,clear_cookies):
        if clear_cookies:
            self.clear_cache()

    def setTarget(self, target):
        self.target = target
        user = self.get_user(target)
        self.target_id = user['id']
        self.is_private = user['is_private']
        self.following = self.check_following()
        self.__printTargetBanner__()

    def __printTargetBanner__(self):
        pc.printout("\nLogged as ", pc.GREEN)
        pc.printout(self.api.username, pc.CYAN)
        pc.printout(". Target: ", pc.GREEN)
        pc.printout(str(self.target), pc.CYAN)
        pc.printout(" [" + str(self.target_id) + "]")
        if self.is_private:
            pc.printout(" [PRIVATE PROFILE]", pc.BLUE)
        if self.following:
            pc.printout(" [FOLLOWING]", pc.GREEN)
        else:
            pc.printout(" [NOT FOLLOWING]", pc.RED)

        print('\n')

    def change_target(self):
        pc.printout("Insert new target username: ", pc.YELLOW)
        line = input()
        self.setTarget(line)
        return

    def get_user(self, username):
        try:
            content = self.api.username_info(username)
            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_user_id.txt"
                file = open(file_name, "w")
                file.write(str(content['user']['pk']))
                file.close()

            user = dict()
            user['id'] = content['user']['pk']
            user['is_private'] = content['user']['is_private']

            return user
        except ClientError as e:
            pc.printout('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response), pc.RED)
            error = json.loads(e.error_response)
            if 'message' in error:
                print(error['message'])
            if 'error_title' in error:
                print(error['error_title'])
            if 'challenge' in error:
                print("Please follow this link to complete the challenge: " + error['challenge']['url'])    
            sys.exit(2)
        
    def set_write_file(self, flag):
        if flag:
            pc.printout("Write to file: ")
            pc.printout("enabled", pc.GREEN)
            pc.printout("\n")
        else:
            pc.printout("Write to file: ")
            pc.printout("disabled", pc.RED)
            pc.printout("\n")

        self.writeFile = flag

    def set_json_dump(self, flag):
        if flag:
            pc.printout("Export to JSON: ")
            pc.printout("enabled", pc.GREEN)
            pc.printout("\n")
        else:
            pc.printout("Export to JSON: ")
            pc.printout("disabled", pc.RED)
            pc.printout("\n")

        self.jsonDump = flag

    def login(self, u, p):
        try:
            settings_file = "config/settings.json"
            if not os.path.isfile(settings_file):
                # settings file does not exist
                print(f'Unable to find file: {settings_file!s}')

                # login new
                self.api = AppClient(auto_patch=True, authenticate=True, username=u, password=p,
                                     on_login=lambda x: self.onlogin_callback(x, settings_file))

            else:
                with open(settings_file) as file_data:
                    cached_settings = json.load(file_data, object_hook=self.from_json)
                # print('Reusing settings: {0!s}'.format(settings_file))

                # reuse auth settings
                self.api = AppClient(
                    username=u, password=p,
                    settings=cached_settings,
                    on_login=lambda x: self.onlogin_callback(x, settings_file))

        except (ClientCookieExpiredError, ClientLoginRequiredError) as e:
            print(f'ClientCookieExpiredError/ClientLoginRequiredError: {e!s}')

            # Login expired
            # Do relogin but use default ua, keys and such
            self.api = AppClient(auto_patch=True, authenticate=True, username=u, password=p,
                                 on_login=lambda x: self.onlogin_callback(x, settings_file))

        except ClientError as e:
            pc.printout('ClientError {0!s} (Code: {1:d}, Response: {2!s})'.format(e.msg, e.code, e.error_response), pc.RED)
            error = json.loads(e.error_response)
            pc.printout(error['message'], pc.RED)
            pc.printout(": ", pc.RED)
            pc.printout(e.msg, pc.RED)
            pc.printout("\n")
            if 'challenge' in error:
                print("Please follow this link to complete the challenge: " + error['challenge']['url'])
            exit(9)

    def to_json(self, python_object):
        if isinstance(python_object, bytes):
            return {'__class__': 'bytes',
                    '__value__': codecs.encode(python_object, 'base64').decode()}
        raise TypeError(repr(python_object) + ' is not JSON serializable')

    def from_json(self, json_object):
        if '__class__' in json_object and json_object['__class__'] == 'bytes':
            return codecs.decode(json_object['__value__'].encode(), 'base64')
        return json_object

    def onlogin_callback(self, api, new_settings_file):
        cache_settings = api.settings
        with open(new_settings_file, 'w') as outfile:
            json.dump(cache_settings, outfile, default=self.to_json)

    def check_following(self):
        if str(self.target_id) == self.api.authenticated_user_id:
            return True
        endpoint = 'users/{user_id!s}/full_detail_info/'.format(**{'user_id': self.target_id})
        return self.api._call_api(endpoint)['user_detail']['user']['friendship_status']['following']

    def check_private_profile(self):
        if self.is_private and not self.following:
            pc.printout("Impossible to execute command: user has private profile\n", pc.RED)
            send = input("Do you want send a follow request? [Y/N]: ")
            if send.lower() == "y":
                self.api.friendships_create(self.target_id)
                print("Sent a follow request to target. Use this command after target accepting the request.")

            return True
        return False
  
    def get_comments(self):
        if self.check_private_profile():
            return

        pc.printout("Searching for users who commented...\n")

        data = self.__get_feed__()
        users = []

        for post in data:
            comments = self.__get_comments__(post['id'])
            for comment in comments:
                print(comment['text'])
                
                # if not any(u['id'] == comment['user']['pk'] for u in users):
                #     user = {
                #         'id': comment['user']['pk'],
                #         'username': comment['user']['username'],
                #         'full_name': comment['user']['full_name'],
                #         'counter': 1
                #     }
                #     users.append(user)
                # else:
                #     for user in users:
                #         if user['id'] == comment['user']['pk']:
                #             user['counter'] += 1
                #             break

        if len(users) > 0:
            ssort = sorted(users, key=lambda value: value['counter'], reverse=True)

            json_data = {}

            t = PrettyTable()

            t.field_names = ['Comments', 'ID', 'Username', 'Full Name']
            t.align["Comments"] = "l"
            t.align["ID"] = "l"
            t.align["Username"] = "l"
            t.align["Full Name"] = "l"

            for u in ssort:
                t.add_row([str(u['counter']), u['id'], u['username'], u['full_name']])

            print(t)

            if self.writeFile:
                file_name = self.output_dir + "/" + self.target + "_users_who_commented.txt"
                file = open(file_name, "w")
                file.write(str(t))
                file.close()

            if self.jsonDump:
                json_data['users_who_commented'] = ssort
                json_file_name = self.output_dir + "/" + self.target + "_users_who_commented.json"
                with open(json_file_name, 'w') as f:
                    json.dump(json_data, f)
        else:
            pc.printout("Sorry! No results found :-(\n", pc.RED)

    def clear_cache(self):
        try:
            f = open("config/settings.json",'w')
            f.write("{}")
            pc.printout("Cache Cleared.\n",pc.GREEN)
        except FileNotFoundError:
            pc.printout("Settings.json don't exist.\n",pc.RED)
        finally:
            f.close()

    def get_followings(self):
        if self.check_private_profile():
            return
        csv_file = self.output_dir + "/" + self.target +  "/" + "_following.csv"
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)

        try:
            next_max_id = None
            pc.printout("do you want to continue last scrape? y/n: ", pc.YELLOW)
            value = input()
            if value == "y":
                pc.printout("Please input last MAX_ID to continue last scrape?", pc.YELLOW)
                next_max_id = input()
            pc.printout("Searching for target followers...\n")
            rank_token = AppClient.generate_uuid()
            if next_max_id is None:
                data = self.api.user_following(str(self.target_id), rank_token=rank_token)
                next_max_id = data.get('next_max_id')
                total = 0
                for user in data.get('users', []):
                    total += 1
                    with open(csv_file, 'a') as f:
                        writer = csv.writer(f)
                        writer.writerow([str(user['pk']), user['username'], user['full_name'],str(next_max_id)])

                    sys.stdout.write("\rCatched %i data" % total)
                    sys.stdout.flush()
                
            count = 0
            while next_max_id:
                data = self.api.user_following(str(self.target_id), rank_token=rank_token, max_id=next_max_id)
                for user in data.get('users', []):
                    total += 1
                    with open(csv_file, 'a') as f:
                        writer = csv.writer(f)
                        writer.writerow([str(user['pk']), user['username'], user['full_name'],str(next_max_id)])

                    sys.stdout.write("\rCatched %i data" % total)
                    sys.stdout.flush()
                next_max_id = data.get('next_max_id')
                if count == 100:
                    settime = random.randint(10, 100)
                    sys.stdout.flush()
                    sys.stdout.write("sleep after seconds."+str(settime))
                    time.sleep(settime)
                    count = 0
                count += 1

            print("done")
        except Exception as e:
            print("\nError.")
            print(str(e))
            print("\n")

    def get_followers(self):
        if self.check_private_profile():
            return
        csv_file = self.output_dir + "/" + self.target +  "/" + "_follower.csv"
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)

        try:
            next_max_id = None
            pc.printout("do you want to continue last scrape? y/n: ", pc.YELLOW)
            value = input()
            if value == "y":
                pc.printout("Please input last MAX_ID to continue last scrape?", pc.YELLOW)
                next_max_id = input()
            pc.printout("Searching for target followers...\n")
            rank_token = AppClient.generate_uuid()
            total = 0
            if next_max_id is None:
                data = self.api.user_followers(str(self.target_id), rank_token=rank_token)
                next_max_id = data.get('next_max_id')
                for user in data.get('users', []):
                    total += 1
                    with open(csv_file, 'a') as f:
                        writer = csv.writer(f)
                        writer.writerow([str(user['pk']), user['username'], user['full_name'],str(next_max_id)])

                    sys.stdout.write("\rCatched %i data" % total)
                    sys.stdout.flush()
            else:
                data = self.api.user_followers(str(self.target_id), rank_token=rank_token, max_id=next_max_id)
                next_max_id = data.get('next_max_id')

                
            count = 0
            while next_max_id:
                data = self.api.user_followers(str(self.target_id), rank_token=rank_token, max_id=next_max_id)
                for user in data.get('users', []):
                    total += 1
                    with open(csv_file, 'a') as f:
                        writer = csv.writer(f)
                        writer.writerow([str(user['pk']), user['username'], user['full_name'],str(next_max_id)])

                    sys.stdout.write("\rCatched %i data" % total)
                    sys.stdout.flush()
                next_max_id = data.get('next_max_id')
                if count >= 100:
                    settime = random.randint(100, 300)
                    sys.stdout.write("sleep after seconds."+str(settime))
                    sys.stdout.flush()
                    time.sleep(settime)
                    count = 0
                else:
                    lottery = random.randint(1, 2)
                    settime = random.randint(0, 10)
                    sys.stdout.write("short sleep after seconds."+str(settime))
                    sys.stdout.flush()
                    time.sleep(settime)
                    if lottery == 1:
                        self.do_random_req()
                count += 1

            print("done")
            text = "Success fetched all {} followers data.".format(self.target)
            self.send_notif(chat_id=-660426638,text=text)
        except Exception as e:
            print("\nError.")
            print(str(e))
            print("\n")
            text = "user : {} \nFailed please check the log. {} followers data. \nerror : {}".format(self.api.username,self.target,str(e))
            self.send_notif(chat_id=-660426638,text=text)

    def get_detail_followings(self):
        try:
            index = 0
            pc.printout("do you want to continue last scrape? y/n: ", pc.YELLOW)
            value = input()
            if value == "y":
                pc.printout("Please input last index to continue last scrape? ", pc.YELLOW)
                index = input()

            csv_file = self.output_dir + "/" + self.target + "/" + "_following.csv"
            target_phone = self.output_dir + "/" + self.target + "/" + "_following_number.csv"
            target_email = self.output_dir + "/" + self.target + "/" + "_following_email.csv"

            os.makedirs(os.path.dirname(csv_file), exist_ok=True)
            # get followers user info
            count = 0
            with open(csv_file) as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                for _ in range(0,int(index)):
                    next(csv_reader)
                line = int(index)
                for row in csv_reader:
                    sys.stdout.write("line data checked "+str(line)+"\n")
                    sys.stdout.flush()
                    user = self.api.user_info(str(row[0]))
                    if 'contact_phone_number' in user['user'] and user['user']['contact_phone_number']:
                        with open(target_phone, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([str(line),str(user['user']['pk']), user['user']['username'], user['user']['full_name'],user['user']['contact_phone_number'],'contact_phone_number'])
                    if 'public_email' in user['user'] and user['user']['public_email']:
                        with open(target_email, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([str(line),str(user['user']['pk']), user['user']['username'], user['user']['full_name'],user['user']['public_email'],'email'])
                    if count >= 100:
                        settime = random.randint(10, 100)
                        sys.stdout.write("sleep after seconds."+str(settime))
                        sys.stdout.flush()
                        time.sleep(settime)
                        count = 0
                    count += 1
                    line += 1
            
        except Exception as e:
            print("\nError.")
            print(str(e))
            print("\n")

    def get_detail_followers(self):
        if self.check_private_profile():
            return
        index = 0
        pc.printout("do you want to continue last scrape? y/n: ", pc.YELLOW)
        value = input()
        if value == "y":
            pc.printout("Please input last index to continue last scrape? ", pc.YELLOW)
            index = input()

        csv_file = self.output_dir + "/" + self.target + "/" + "_follower.csv"
        target_phone = self.output_dir + "/" + self.target + "/" + "_follower_number.csv"
        target_email = self.output_dir + "/" + self.target + "/" + "_follower_email.csv"

        os.makedirs(os.path.dirname(csv_file), exist_ok=True)
        # get followers user info
        count = 0
        with open(csv_file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for _ in range(0,int(index)):
                next(csv_reader)
            line = int(index)
            for row in csv_reader:
                try:
                    sys.stdout.write("\n"+"line data checked "+str(line)+"\n")
                    sys.stdout.flush()
                    
                    user = self.api.user_info(str(row[0]))
                    if 'contact_phone_number' in user['user'] and user['user']['contact_phone_number']:
                        with open(target_phone, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([str(line),str(user['user']['pk']), user['user']['username'], user['user']['full_name'],user['user']['contact_phone_number'],'contact_phone_number'])
                    
                    if 'public_email' in user['user'] and user['user']['public_email']:
                        with open(target_email, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([str(line),str(user['user']['pk']), user['user']['username'], user['user']['full_name'],user['user']['public_email'],'email'])

                    if count >= 200:
                        settime = random.randint(100, 300)
                        sys.stdout.write("sleep after seconds."+str(settime))
                        sys.stdout.flush()
                        # time.sleep(settime)
                        count = 0
                    else:
                        lottery = random.randint(1, 2)
                        if lottery == 1:
                            settime = random.randint(0, 10)
                            sys.stdout.write("short sleep after seconds."+str(settime))
                            sys.stdout.flush()
                            # time.sleep(settime)
                        # else:
                        #     self.do_random_req()
                    count += 1
                    line += 1
                except Exception as e:
                    print("\nError.")
                    print(str(e))
                    settime = random.randint(10, 20)
                    # text = """
                    # User : {}
                    # \nTarget : {}
                    # \n\nFAILED TO GET DETAIL FOLLOWER DATA.
                    # \nLast user checked : {}.
                    # \nError : {}.
                    # \n\nAutomatically try again in {} second
                    # """.format(self.api.username,self.target,str(line),str(e),str(settime))
                    # self.send_notif(chat_id=-660426638,text=text)
                    # time.sleep(settime)


        text = "Success fetched all {} followers phone number. \n".format(self.target)
        self.send_notif(chat_id=-660426638,text=text)

    def search_username(self):
        pc.printout("input search query? ", pc.YELLOW)
        name = input()
        target_phone = self.output_dir + "/result_" + name +  "/" + "user_phone.csv"
        os.makedirs(os.path.dirname(target_phone), exist_ok=True)

        target_email = self.output_dir + "/result_" + name +  "/" + "user_email.csv"
        os.makedirs(os.path.dirname(target_email), exist_ok=True)

        result = self.api.search_users(name)
        for user in result.get('users', []):
                try:
                    user = self.api.user_info(str(user['pk']))
                    if 'contact_phone_number' in user['user'] and user['user']['contact_phone_number']:
                        with open(target_phone, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([str(user['user']['pk']), user['user']['username'], user['user']['full_name'],user['user']['contact_phone_number'],'contact_phone_number'])
                    
                    if 'public_email' in user['user'] and user['user']['public_email']:
                        with open(target_email, 'a') as f:
                            writer = csv.writer(f)
                            writer.writerow([str(user['user']['pk']), user['user']['username'], user['user']['full_name'],user['user']['public_email'],'email'])
                except Exception as e:
                    print("\nError.")
                    print(str(e))


    def do_random_req(self):
        if self.check_private_profile():
            return
        number = random.randint(1,10)
        print("\n===== doing random request ======")
        print(number)
        print("===== doing random request ======\n")
        try:
            if number == 1:
                result = self.api.user_feed(str(self.target_id))
            elif number == 2:
                endpoint = 'users/{user_id!s}/full_detail_info/'.format(**{'user_id': self.target_id})
                result = self.api._call_api(endpoint)
            elif number == 3:
                result = self.api.search_users(names.get_first_name())
            elif number == 4:
                result = self.api.blocked_user_list()
            elif number == 5:
                result = self.api.tags_user_following(str(self.target_id))
            elif number == 6:
                result = self.api.tag_follow_suggestions()
            else:
                r = RandomWords()
                rank_token = AppClient.generate_uuid()
                result = self.api.tag_search(text=r.get_random_word(),rank_token=rank_token)
            print(result)
        except Exception as e:
            return str(e)
        return True

    def send_notif(self, chat_id, text):
        url = "https://api.telegram.org//sendMessage?chat_id={}&text={}".format(chat_id, text)
        # with open("config/settings.json", 'w') as f:
        #     f.write("{}")
        # u = config.getUsername()
        # p = config.getPassword()
        # self.login(p=p,u=u)
        # return url
        payload={}
        headers = {}

        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.text)
        return response.text
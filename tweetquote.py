#!/usr/bin/python3

from ast import Raise
import base64
from curses.has_key import has_key
import datetime
import json
import os
from telnetlib import theNULL
import requests
import tweepy
import yaml
import glob
import random

# image libraries
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# some constants
SCRIPT_VERSION = 1.10

CONFIG_ERROR = 100
API_ERROR    = 200
IMAGE_ERROR  = 300

#
# sample response from service
#
#    {
#        'version': 'v1.13',
#        'service': 'GetRandomAuthorWithQuote',
#        'generated': '2021-07-19 20:29:45',
#        'author': {
#            'id': 3,
#            'name': 'Dag Hammarskjold',
#            'period': '',
#            'added': '2017-08-10 13:14:10',
#            'aliases': [{
#                'id': 23,
#                'name': 'Dag Hjalmar Agne Carl Hammarskjold',
#                'added': '2018-08-28 11:48:42'
#            }],
#            'quote': {
#                'id': 2813,
#                'text': 'Never look down to test the ground before taking your next step; only he who keeps his eye fixed on the far horizon will find the right road.',
#                'used': 0,
#                'added': '2018-08-28 11:49:02'
#            }
#        }
#    }


class GeneralError(Exception):
    """Exception raised for catching various problems.

    Attributes:
        code -- this may be either a default or a code from the service
        message -- we might get a message to use
    """
    def __init__(self, code, message="Unknown Error"):
        self.code = code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.code} -> {self.message}'

def checkMandatoryConfigurationExists(cfg, mandatory_keys, error_message):
    missing_keys = []
    for item in mandatory_keys:
        if item not in cfg:
            missing_keys.append(item)
    # missing any and we want to kill the script
    if len(missing_keys) > 0:
        message = error_message
        for item in missing_keys:
            message += ' ' + item
        raise GeneralError(CONFIG_ERROR, message + '!')
    return

# get current dt and print
def getCurrentDateTimeAsString():
    return datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')

# general print for logging
def printProgress(stage, extra):
    message = '[ ' + getCurrentDateTimeAsString() + ' ]:' + os.path.basename(__file__) + ':' + 'v{:.2f}'.format(SCRIPT_VERSION) + ':' + stage
    if extra != '':
        message = message + ':' + extra
    print(message)
    return

# get list of image files we could use and return a random item
def getRandomFile(path):
    fileList = glob.glob(path)
    if len(fileList) == 0:
        raise GeneralError(IMAGE_ERROR, 'Failed to find images to use!')
    return random.choice(fileList)

# do we have a JSON str
def isJSON(str):
    try:
        json.loads(str)
    except ValueError as e:
        return False
    return True

# get a random quote
def getRandomQuote(apiUrl, apiToken):
    headers_api = {
        'accept': 'application/json',
        'Authorization': 'Bearer ' + apiToken,
    }
    params = (
    )
    response = requests.get(apiUrl, headers=headers_api, params=params, verify=False)
    # on an error check if the API returned an internal api generated error (in JSON) or a tragic HTML response error ie. 404
    if response.status_code != 200:
        if isJSON(response.content.decode()):
            json_string = response.json()
            raise GeneralError(json_string['code'], json_string['message'])
        else:
            raise GeneralError(response.status_code, 'API crashed and burned!')
    return response.json()

def main():
    try:
        printProgress('Loading configuration', '')
        with open('tweetquote.yaml', 'r') as ymlfile:
            cfg = yaml.full_load(ymlfile)

        checkMandatoryConfigurationExists(cfg['api'], ['url', 'token'], 'Quote API details missing:')
        checkMandatoryConfigurationExists(cfg['twitter'], ['consumer_key', 'consumer_secret', 'access_token', 'access_token_secret'], 'Twitter API auth details missing:')
        checkMandatoryConfigurationExists(cfg['images'], ['path', 'ext', 'name', 'format'], 'Image configuration missing:')

        # get a quote
        json_string = getRandomQuote(cfg['api']['url'], cfg['api']['token'])

        tweet =  '\'' + json_string['author']['quote']['text'] + '\'\n\n' + json_string['author']['name']

        # go and tweet!
        auth = tweepy.OAuthHandler(
                cfg['twitter']['consumer_key'],
                cfg['twitter']['consumer_secret']
                )
        auth.set_access_token(
                cfg['twitter']['access_token'],
                cfg['twitter']['access_token_secret']
                )

        printProgress('Tweeting', json.dumps(json_string))
        api = tweepy.API(auth)
        status = api.update_status(status=tweet)
        printProgress('Finishing', '')
    except GeneralError as e:
        print()
        print('ErrorCode: (' + str(e.code) + '), ErrorMessage: ' + e.message)
    finally:
        print()

if __name__ == '__main__':
    main()
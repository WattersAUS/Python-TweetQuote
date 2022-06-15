#!/usr/bin/python3

# Authorization data

import base64
import datetime
import json
import os
from telnetlib import theNULL
import requests
import tweepy
import yaml

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

# get current dt and print

def getCurrentDateTimeAsString():
    return datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')

# general print for logging

def printProgress(stage, extra):
    message = '[ ' + getCurrentDateTimeAsString() + ' ]:' + os.path.basename(__file__) + ':' + stage
    if extra != '':
        message = message + ':' + extra
    print(message)
    return

# should the api call crash and burn, die gracefully

class APIResponseError(Exception):
    pass

def api_error_response(response):
    printProgress('API error', json.dumps(response.json()))
    raise APIResponseError(response)

# get a random quote but we need to be mindful we don't exceed the max length of a tweet

def getRandomQuote(apiUrl, apiToken):
    headersAPI = {
        'accept': 'application/json',
        'Authorization': 'Bearer ' + apiToken,
    }
    params = (
    )
    response = requests.get(apiUrl, headers=headersAPI, params=params, verify=False)
    if response.status_code == 200:
        return response.json()

    api_error_response(response)
    return api_response

def main():

    try:
        printProgress('Starting', '')
        with open('tweetquote.yaml', 'r') as ymlfile:
            cfg = yaml.full_load(ymlfile)

# get the quote 

        json_string = getRandomQuote(cfg['api']['url'], cfg['api']['token'])
        tweet =  '\'' + json_string['author']['quote']['text'] + '\'\n\n' + json_string['author']['name']

# Using authentication keys created on the Twitter dev account to make API calls

        auth = tweepy.OAuthHandler(
                cfg['twitter_auth_keys']['consumer_key'],
                cfg['twitter_auth_keys']['consumer_secret']
                )
        auth.set_access_token(
                cfg['twitter_auth_keys']['access_token'],
                cfg['twitter_auth_keys']['access_token_secret']
                )

        printProgress('Tweeting', json.dumps(json_string))
        api = tweepy.API(auth)

        status = api.update_status(status=tweet)
    finally:
        printProgress('Finishing', '')

if __name__ == '__main__':
    main()
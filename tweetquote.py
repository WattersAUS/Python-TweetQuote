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
from textwrap import wrap
import string

# image libraries
from PIL import Image, ImageDraw, ImageFont

# some constants
SCRIPT_VERSION = 2.03

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

def validateConfiguration(cfg):
    checkMandatoryConfigurationExists(cfg['api'], ['url', 'token'], 'Quote API details missing:')
    checkMandatoryConfigurationExists(cfg['twitter'], ['consumer_key', 'consumer_secret', 'access_token', 'access_token_secret'], 'Twitter API auth details missing:')
    checkMandatoryConfigurationExists(cfg['images'], ['path', 'prefix', 'format', 'height', 'width', 'bgcolour', 'textcolour'], 'Image configuration missing:')
    checkMandatoryConfigurationExists(cfg['font'], ['family', 'size', 'char_limit', 'margin'], 'Font configuration missing:')
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

# get positions for each line of the quote 
def get_y_and_heights(text_wrapped, dimensions, margin, font):
    """Get the first vertical coordinate at which to draw text and the height of each line of text"""
    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()
    # Calculate the height needed to draw each line of text (including its bottom margin)
    line_heights = [
        font.getmask(text_line).getbbox()[3] + descent + margin
        for text_line in text_wrapped
    ]
    # The last line doesn't have a bottom margin
    line_heights[-1] -= margin
    # Total height needed
    height_text = sum(line_heights)
    # Calculate the Y coordinate at which to draw the first line of text
    y = (dimensions[1] - height_text) // 2
    # Return the first Y coordinate and a list with the height of each line
    return (y, line_heights)

def buildQuoteImage(images_cfg, fonts_cfg, quote, author):
    font = ImageFont.truetype(fonts_cfg['family'], fonts_cfg['size'])
    ascent, descent = font.getmetrics()

    # author text dimenions used to position the 'author' at the bottom right of the image
    author_width = font.getmask(author).getbbox()[2]
    author_height = font.getmask(author).getbbox()[3] + descent

    # build the image
    image = Image.new("RGB", (images_cfg['width'], images_cfg['height']), color=images_cfg['bgcolour'])
    draw = ImageDraw.Draw(image)
    # place the author
    draw.text((images_cfg['width'] - fonts_cfg['margin'] - author_width, images_cfg['height'] - fonts_cfg['margin'] - author_height), author, fill=(0, 0, 0), font=font)

    # if the quote will span multiple lines we'll need to split it into an array
    quote_lines = wrap(quote, fonts_cfg['char_limit'])

    # Get the first vertical coordinate at which to draw text and the height of each line of text
    y, line_heights = get_y_and_heights(
        quote_lines,
        (images_cfg['width'], images_cfg['height'] - ((fonts_cfg['margin'] * 2) + author_height)),
        fonts_cfg['margin'],
        font
    )

    # Draw each line of the quote
    for i, line in enumerate(quote_lines):
        # Calculate the horizontally-centered position at which to draw this line
        line_width = font.getmask(line).getbbox()[2]
        x = ((images_cfg['width'] - line_width) // 2)
        # Draw this line
        draw.text((x, y), line, font=font, fill=(0, 0, 0))
        # Move on to the height at which the next line should be drawn at
        y += line_heights[i]

    # add a fancy border around the edge of the image
    draw.line([(20, 5), (images_cfg['width'] - 20, 5)], fill ="black", width = 4)
    draw.line([(images_cfg['width'] - 20, 5),(images_cfg['width'] - 5, 20)], fill ="black", width = 4)

    draw.line([(images_cfg['width'] - 5, 20), (images_cfg['width'] - 5, images_cfg['height'] - 20)], fill ="black", width = 4)
    draw.line([(images_cfg['width'] - 5, images_cfg['height'] - 20), (images_cfg['width'] - 20, images_cfg['height'] - 5)], fill ="black", width = 4)

    draw.line([(images_cfg['width'] - 20, images_cfg['height'] - 5), (20, images_cfg['height'] - 5)], fill ="black", width = 4)
    draw.line([(20, images_cfg['height'] - 5), 5, (images_cfg['height'] - 20)], fill ="black", width = 4)
    
    draw.line([5, (images_cfg['height'] - 20), (5, 20)], fill ="black", width = 4)
    draw.line([(5, 20), (20, 5)], fill ="black", width = 4)
    return image

def tweetQuoteImage(twitter_cfg, author, image):
    auth = tweepy.OAuthHandler(
        twitter_cfg['consumer_key'],
        twitter_cfg['consumer_secret']
    )
    auth.set_access_token(
        twitter_cfg['access_token'],
        twitter_cfg['access_token_secret']
    )
    api = tweepy.API(auth)
    author = author.translate(str.maketrans('', '', string.punctuation)).replace(" ", "")
    media = api.media_upload(image)
    tweet = "Words of wisdom. #" + author
    post_result = api.update_status(status=tweet, media_ids=[media.media_id])
    return

def main():
    try:
        printProgress('Starting up', '')
        with open('tweetquote.yaml', 'r') as ymlfile:
            cfg = yaml.full_load(ymlfile)

        validateConfiguration(cfg)
        quote = getRandomQuote(cfg['api']['url'], cfg['api']['token'])
        printProgress('Quote retrieved', json.dumps(quote))
        image = buildQuoteImage(cfg['images'], cfg['font'], quote['author']['quote']['text'], quote['author']['name'])
        new_image_name = cfg['images']['path'] + '/' + cfg['images']['prefix'] + 'generatedimage'
        image.save(new_image_name, 'png')
        printProgress('Tweeting words of wisdom!', '')
        tweetQuoteImage(cfg['twitter'], quote['author']['name'], new_image_name)
        printProgress('Finishing', '')
    except GeneralError as e:
        print()
        print('ErrorCode: (' + str(e.code) + '), ErrorMessage: ' + e.message)
    finally:
        print()

if __name__ == '__main__':
    main()
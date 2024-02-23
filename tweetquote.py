#!/usr/bin/python3

import sys
from ast import Raise
import base64
from curses.has_key import has_key
import datetime
import json
import os
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
SCRIPT_VERSION = 3.11

CONFIG_ERROR = 100
API_ERROR    = 200
IMAGE_ERROR  = 300
RENDER_ERROR = 400

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
    checkMandatoryConfigurationExists(cfg['images']['generated'], ['path', 'prefix', 'format', 'height', 'width', 'bgcolour'], 'Image generation configuration missing:')
    checkMandatoryConfigurationExists(cfg['images']['library'], ['path', 'prefix'], 'Image library configuration missing:')
    checkMandatoryConfigurationExists(cfg['font'], ['family', 'size', 'textcolour', 'char_limit', 'margin'], 'Font configuration missing:')
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

# get positions for the start of the first line and all the heights for subsequent lines 
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

# we should have an array of possible bgcolours to use, if not default to white
def selectBackgroundColour(images_cfg):
    bgcolour = "white"
    if len(images_cfg['bgcolour']) > 0:
        bgcolour = random.choice(images_cfg['bgcolour'])
        printProgress('Found ' + str(len(images_cfg['bgcolour'])) + ' background colours to choose from, selected ' + bgcolour + '!', '')
    return bgcolour

# draw a black border just inside the image boundary
def drawImageBorder(draw, fill_colour, image_height, image_width, margin, ident, border):
    draw.line([(ident, margin), (image_width - ident, margin)], fill =fill_colour, width = border)
    draw.line([(image_width - ident, margin),(image_width - margin, ident)], fill =fill_colour, width = border)
    draw.line([(image_width - margin, ident), (image_width - margin, image_height - ident)], fill =fill_colour, width = border)
    draw.line([(image_width - margin, image_height - ident), (image_width - ident, image_height - margin)], fill =fill_colour, width = border)
    draw.line([(image_width - ident, image_height - margin), (ident, image_height - margin)], fill =fill_colour, width = border)
    draw.line([(ident, image_height - margin), margin, (image_height - ident)], fill =fill_colour, width = border)
    draw.line([margin, (image_height - ident), (margin, ident)], fill =fill_colour, width = border)
    draw.line([(margin, ident), (ident, margin)], fill =fill_colour, width = border)
    return

def createImage(images_cfg):
    return Image.new("RGB", (images_cfg['width'], images_cfg['height']), color=selectBackgroundColour(images_cfg))


def getAuthorFontandTextWidthHeight(author, font_cfg):
    font = ImageFont.truetype(font_cfg['family'], font_cfg['size'])
    ascent, descent = font.getmetrics()
    author_width = font.getmask(author).getbbox()[2]
    author_height = font.getmask(author).getbbox()[3] + descent
    return (font, author_width, author_height)

def placeQuoteOntoImage(image, image_height, image_width, fonts_cfg, quote, author):
    # author text details used to position the 'author' text at the bottom right of the image
    font, author_width, author_height = getAuthorFontandTextWidthHeight(author, fonts_cfg)

    # build the image
    draw = ImageDraw.Draw(image)

    # place the author
    draw.text((image_width - fonts_cfg['margin'] - author_width, image_height - fonts_cfg['margin'] - author_height), author, fill=fonts_cfg['textcolour'], font=font)

    # for the quote try to fit the text onto the image using the default font size
    # if that doesn't fit reduce the size until it does or give up if it gets too small
    fontsize = fonts_cfg['size']
    charlimit = fonts_cfg['char_limit']

    while True:
        quote_lines = wrap(quote, charlimit)
        font = ImageFont.truetype(fonts_cfg['family'], fontsize)
        y, line_heights = get_y_and_heights(
            quote_lines,
            (image_width, image_height - ((fonts_cfg['margin'] * 2) + author_height)),
            fonts_cfg['margin'],
            font
        )
        if y > fonts_cfg['margin']:
            break
        fontsize -= 2
        if fontsize < 1:
            raise GeneralError(RENDER_ERROR, 'Unable to render quote as fontsize is now < 1!!!')
        charlimit += 4
        printProgress('Quote starts within margin (' + str(fonts_cfg['margin']) + ' / ' + str(y) + '), using smaller font (' + str(fontsize) + ') with character limit (' + str(charlimit) + '), trying again!', '')

    # Draw each line of the quote
    for i, line in enumerate(quote_lines):
        # Calculate the horizontally-centered position at which to draw this line
        line_width = font.getmask(line).getbbox()[2]
        x = ((image_width - line_width) // 2)
        # Draw a line of the quote
        draw.text((x, y), line, font=font, fill=fonts_cfg['textcolour'])
        # Move on to the height at which the next line should be drawn at
        y += line_heights[i]

    # add a fancy border around the edge of the image
    drawImageBorder(draw, fonts_cfg['textcolour'], image_height, image_width, 5, 20, 3)
    drawImageBorder(draw, fonts_cfg['textcolour'], image_height, image_width, 10, 20, 3)
    return image

def writeQuoteOnExistingImage():
    return

def setAuthAccess(twitter_cfg):
    auth = tweepy.OAuthHandler(
        twitter_cfg['consumer_key'],
        twitter_cfg['consumer_secret']
    )
    auth.set_access_token(
        twitter_cfg['access_token'],
        twitter_cfg['access_token_secret']
    )
    return auth

def uploadImageToTwitter(auth, image):
    api = tweepy.API(auth)
    media = api.media_upload(image)
    return media

def setClientAccess(twitter_cfg):
    client = tweepy.Client(
        consumer_key = twitter_cfg['consumer_key'],
        consumer_secret = twitter_cfg['consumer_secret'],
        access_token = twitter_cfg['access_token'],
        access_token_secret = twitter_cfg['access_token_secret']
    )
    return client

def tweetMessage(client, author, media):
    author = author.translate(str.maketrans('', '', string.punctuation)).replace(" ", "")
    tweet = "Words of wisdom. #" + author
    client.create_tweet(text=tweet, media_ids=[media.media_id])
    return

def getConfigName(script_name):
    cfg_name = script_name.split('.')
    return cfg_name[0] + '.yaml'

def main():
    try:
        printProgress('Starting up script', sys.argv[0])
        cfg_file = getConfigName(sys.argv[0])
        printProgress('Looking for config file', cfg_file)
        with open(cfg_file, 'r') as ymlfile:
            cfg = yaml.full_load(ymlfile)
        validateConfiguration(cfg)
        quote = getRandomQuote(cfg['api']['url'], cfg['api']['token'])
        printProgress('Quote retrieved', json.dumps(quote))
        generated_image = createImage(cfg['images']['generated'])
        quoted_image = placeQuoteOntoImage(generated_image, cfg['images']['generated']['height'], cfg['images']['generated']['width'], cfg['font'], quote['author']['quote']['text'], quote['author']['name'])
        new_image_name = cfg['images']['generated']['path'] + '/' + cfg['images']['generated']['prefix'] + 'generatedimage'
        quoted_image.save(new_image_name, 'png')
        printProgress('Setting Twitter v1 API Authentication object!', '')
        auth = setAuthAccess(cfg['twitter'])
        printProgress('Using Twitter v1 API to upload image with embedded quote!', new_image_name)
        media = uploadImageToTwitter(auth, new_image_name)
        printProgress('Setting Twitter v2 API Authenication object!', '')
        client = setClientAccess(cfg['twitter'])
        printProgress('Using Twitter v2 API to tweet words of wisdom!', '')
        tweetMessage(client, quote['author']['name'], media)    
        printProgress('Finishing', '')
    except GeneralError as e:
        print()
        print('ErrorCode: (' + str(e.code) + '), ErrorMessage: ' + e.message)
    finally:
        print()

if __name__ == '__main__':
    main()

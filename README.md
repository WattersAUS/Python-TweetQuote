# Python-TweetQuote

Files

    tweetquote.py
        - the main python script
    tweetquote.yaml
        - sample configuration file
    sample.json
        - sample response from service used
    logging_example.txt
        - sample log generated from program
    README.md
        - this file

--------------------------------------------------------------------------------------------------------------------------------------------------------------------

The service used to store quotes is also available in a repository this is made up of 2 other parts

1. PHP-QuoteServiceOO
    - API service that returns various responses containing quotes etc (also contains quotes.sql MySQL database that is used to store the quotes)
    
2. PHP-GeneralAccess 
    - Generic routines that are used in the PHP-QuoteServiceOO project and others

--------------------------------------------------------------------------------------------------------------------------------------------------------------------

Thanks To

    José Fernando Costa for publishing this -> https://levelup.gitconnected.com/how-to-properly-calculate-text-size-in-pil-images-17a2cc6f51fd

    It was a great explanation and code sample (which I have shamelessly lifted) for using the PIL library and how to centre text in a image.

--------------------------------------------------------------------------------------------------------------------------------------------------------------------

Notes:
    
    Uses the 'tweepy' twitter python module to do all the hard work with Twitter integration

    The user will also need to setup a Twitter API keys to allow the above project to send the Tweets (yaml config shows what bits it needs)

--------------------------------------------------------------------------------------------------------------------------------------------------------------------

Things still to do:

    Currently I place a limit on the length of the quotes in the version I have deployed. I want to dynamically adjust image / font sizes depending on the quote being rendered.

----------------------------------------------------------- End of Line --------------------------------------------------------------------------------------------


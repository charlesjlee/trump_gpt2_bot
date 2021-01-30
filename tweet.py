import tweepy
import os

consumer_key = os.environ["consumer_key"]
consumer_secret = os.environ["consumer_secret"]
access_token = os.environ["access_token"]
access_token_secret = os.environ["access_token_secret"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

# get list of friends

# TODO: extract the required field, e.g. `id`
# TODO: maybe keep the the display for nice printing/debugging
friend_ids = [x for x in api.friends_ids()]
print(f"friend_ids: {friend_ids}\n")
print('-'*20)

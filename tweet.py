import tweepy
import os
import re
import sys
import os
import time
from pprint import pprint
from aitextgen import aitextgen
import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option('display.max_colwidth', None)

consumer_key = os.environ["consumer_key"]
consumer_secret = os.environ["consumer_secret"]
access_token = os.environ["access_token"]
access_token_secret = os.environ["access_token_secret"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

FILE_PATH = 'processed.csv'
PROMPT_TWEET_ID = 'prompt_tweet_id'
PROMPT_TWEET = 'prompt_tweet'
RESPONSE_TWEET_ID = 'response_tweet_id'
RESPONSE_TWEET = 'response_tweet'
columns = [PROMPT_TWEET_ID, PROMPT_TWEET, RESPONSE_TWEET_ID, RESPONSE_TWEET]

# load processed tweets
try:
    df = pd.read_csv(FILE_PATH, encoding='utf-8')
except FileNotFoundError:
    df = pd.DataFrame(columns=columns)

# TODO: change `count` to 1
# get latest tweet by followers
follower_tweets = [
    # (tweet.id_str, re.sub(r'http\S+', '', tweet.full_text).strip()) # TODO: reapply regex
    (tweet.id_str, tweet.full_text)
    for friend_id in api.friends_ids()
    for tweet in api.user_timeline(
        tweet_mode='extended',
        user_id=friend_id,
        count=3,
        include_rts=False,
        exclude_replies=True,
    )
]
print("follower_tweets")
pprint(follower_tweets)

# get first new, unprocessed tweet
new_tweet = next(filter(lambda x: int(x[0]) not in set(df.prompt_tweet_id), follower_tweets), None)
print(f"{new_tweet=}")

if not new_tweet:
    sys.exit("no new, unprocessed tweets. Aborting!")

# # run through GPT2
# start_time = time.time()
# ai = aitextgen()
# print(f"loaded model in {round(time.time()-start_time, 2)} seconds")

# start_time = time.time()
# ai.generate(n=3, prompt="I believe in unicorns because", max_length=100)
# answers = []
# print(f"generated {len(answers)} results in {round(time.time()-start_time, 2)} seconds")
response_tweet = 'xxxxxxxxxxx'

# tweet as a reply
try:
    status = api.update_status(status=response_tweet,
                               in_reply_to_status_id=new_tweet[0],
                               auto_populate_reply_metadata=True)
except Exception as e:
    sys.exit(f"Failed to tweet as reply because {type(e).__name__} occurred. Arguments:\n{e.args}")

# log tweet
new_df = pd.DataFrame([[*new_tweet, status.id_str, response_tweet]], columns=columns)
new_df.to_csv(FILE_PATH, mode='a', header=not os.path.exists(FILE_PATH), index=False, encoding='utf-8')

print(f"appended new row to {FILE_PATH}:\n{new_df}")
print(42*'-' + '\nScript succeeded!')

import tweepy
import os
import re
from pprint import pprint

consumer_key = os.environ["consumer_key"]
consumer_secret = os.environ["consumer_secret"]
access_token = os.environ["access_token"]
access_token_secret = os.environ["access_token_secret"]

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# get set of processed tweet ID's
with open('processed.txt') as f:
    processed = set(map(str.strip, f.readlines()))
print(f"processed: {processed}\n")

# TODO: change `count` to 1
# get latest tweet by followers
follower_tweets = [
    (tweet.id_str, re.sub(r'http\S+', '', tweet.full_text).strip())
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

# find new, un-processed tweets
new_tweet_ids = {x[0] for x in follower_tweets} - processed
print("new_tweets")
pprint(new_tweet_ids)

if not new_tweet_ids:
    sys.exit("no new tweets. Aborting!")

tweet_id = new_tweet_ids.pop()
print("tweet")
pprint(tweet)

# run through GPT2

# tweet it (as a reply?)
# result = api.update_status("Look, I'm tweeting from #Python in my #earthanalytics class! @EarthLabCU")
result = True

if result:
    with open('processed.txt', 'a') as f:
        f.write(f"{tweet}\n")
else:
    print("failed to tweet!")

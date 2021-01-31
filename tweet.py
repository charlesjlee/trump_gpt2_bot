import tweepy
import os
import re
import sys
import time
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

# get latest tweet by followers
follower_tweets = [
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
print(f"follower_tweets\n{follower_tweets}\n\n")

# get first new, unprocessed tweet
new_tweet = next(filter(lambda x: int(x[0]) not in set(df.prompt_tweet_id), follower_tweets), None)
print(f"{new_tweet=}")

if not new_tweet:
    print(42*'-' + '\nNo new, unprocessed tweets. Aborting!')

else:
    # run through GPT2
    start_time = time.time()
    ai = aitextgen()
    print(f"loaded model in {round(time.time()-start_time, 2)} seconds")
    
    prompt = re.sub(r'http\S+', '', new_tweet[1]).strip() # no image or video links
    t1 = "Immigration reform is fine but don't rush to give away our country! Sounds like that's what's happening."
    t2 = "The Republicans will get zero credit for passing immigration reform and I said zero!"
    t3 = "Randy Moss should not be bragging about himself I'm the only one who is allowed to do that!"
    prompt_updated = f"{prompt} Trump {t1} Trump {t2} Trump {t3} Trump I {prompt}" # magic sauce
    
    def process(s):
        s = s.replace(prompt_updated,'').strip()
        s = re.sub(r'http\S+', '', s).strip()
    
        # strip first and last sentence
        s = s[s.find('.')+1:s.rfind('.')+1].strip()
        if len(s) > 280: s = s[:s.rfind('.')+1].strip()
        if len(s) > 280: s = s[:s.rfind('.')+1].strip()
    
        return s
    
    # ask GPT-2 small model to generate answers
    start_time = time.time()
    answers = list(map(process, ai.generate(n=30, max_length=220, prompt=prompt_updated, return_as_list=True)))
    print(f"generated {len(answers)} results in {round(time.time()-start_time, 2)} seconds")
    
    def jaccard_similarity(a, b):
        x, y = set(a), set(b)
        return len(x&y) / len(x|y)
    
    def score(row):
        if row.len < 10 or row.len > 250 or row.trump or row.symbols > 2: return 0
        return row.jaccard + row.self_similarity
    
    # compute score for each answer
    df = pd.DataFrame({
        'text': answers,
        'len': list(map(len,answers)),
        'trump': [s.lower().count("trump") for s in answers],
        'symbols': [sum(ord(c)>=128 for c in s) for s in answers],
        'jaccard': [1-sum(jaccard_similarity(a,b) for b in [t1,t2,t3])/3 for a in answers],
        'self_similarity': [len(set(s))/len(s) if len(s) else 1 for s in answers],
    })
    df['score'] = df.apply(score, axis=1)
    df.sort_values(by='score', ascending=False, inplace=True)
    print(f"\nTop 10 answers by score\n{42*'-'}\n{df.head(10)}\n")
    
    # choose randomly from score range of [0.4, 0.65]
    # shorter lengths score too high
    response = df[(0.4<df.score) & (df.score <0.65)].sample()
    print(f"Randomly selected response: {response}\n")
    
    # tweet as a reply
    try:
        status = api.update_status(status=response.text.item(),
                                   in_reply_to_status_id=new_tweet[0],
                                   auto_populate_reply_metadata=True)
    except Exception as e:
        sys.exit(f"Failed to tweet as reply because {type(e).__name__} occurred. Arguments:\n{e.args}")
    
    # log tweet
    log_df = pd.DataFrame([[*new_tweet, status.id_str, response.text.item()]], columns=columns)
    log_df.to_csv(FILE_PATH, mode='a', header=not os.path.exists(FILE_PATH), index=False, encoding='utf-8')
    
    print(f"appended new row to {FILE_PATH}:\n{log_df}")
    print(42*'-' + '\nScript succeeded!')

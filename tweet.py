import tweepy
import os
import re
import sys
import time
from wordfilter import Wordfilter
from string import punctuation
from collections import Counter
from aitextgen import aitextgen
from tenacity import retry, wait_exponential, stop_after_attempt

import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option('display.max_colwidth', None)

consumer_key = os.environ["consumer_key"]
consumer_secret = os.environ["consumer_secret"]
access_token = os.environ["access_token"]
access_token_secret = os.environ["access_token_secret"]

FILE_PATH = 'processed.csv'
COLUMNS = ['prompt_tweet_id', 'prompt_tweet', 'response_tweet_id', 'response_tweet']

wordfilter = Wordfilter()
wordfilter.addWords(['hitler','kill'])

PROMPT_FLAVOR_1 = "Immigration reform is fine but don't rush to give away our country! Sounds like that's what's happening."
PROMPT_FLAVOR_2 = "The Republicans will get zero credit for passing immigration reform and I said zero!"
PROMPT_FLAVOR_3 = "Randy Moss should not be bragging about himself I'm the only one who is allowed to do that!"

def load_processed_tweets():
    try:
        return pd.read_csv(FILE_PATH, encoding='utf-8')
    except FileNotFoundError:
        return pd.DataFrame(columns=COLUMNS)

@retry(wait=wait_exponential(multiplier=1, min=1, max=60), stop=stop_after_attempt(5))
def get_latest_tweets_by_followers(api, count=10):
    follower_tweets = [
        (tweet.id_str, tweet.full_text)
        for friend_id in api.get_friend_ids()
        for tweet in api.user_timeline(
            tweet_mode='extended',
            user_id=friend_id,
            count=count,
            include_rts=False,
            exclude_replies=True,
        )
    ]
    print(f"follower_tweets\n{follower_tweets}\n\n")
    return follower_tweets

@retry(wait=wait_exponential(multiplier=1, min=1, max=60), stop=stop_after_attempt(5))
def load_aitextgen():
    # run through GPT-2 small model
    start_time = time.time()

    ai = aitextgen()
    print(f"loaded aitextgen model in {round(time.time()-start_time, 2)} seconds")
    return ai

def generate_candidate_tweets(ai, tweet_text):
    prompt = re.sub(r'http\S+', '', tweet_text).strip() # no image or video links
    prompt_updated = f"{prompt} Trump {PROMPT_FLAVOR_1} Trump {PROMPT_FLAVOR_2} Trump {PROMPT_FLAVOR_3} Trump I {prompt}" # magic sauce
    
    def process(s):
        s = s.replace(prompt_updated,'').strip()
        s = re.sub(r'http\S+', '', s).strip()
    
        # strip first and last sentence
        s = s[s.find('.')+1:s.rfind('.')+1].strip()
        if len(s) > 280: s = s[:s.rfind('.')+1].strip()
        if len(s) > 280: s = s[:s.rfind('.')+1].strip()
    
        return s
    
    start_time = time.time()
    candidate_tweets = list(map(process, ai.generate(n=60, max_length=220, prompt=prompt_updated, return_as_list=True)))
    print(f"generated {len(candidate_tweets)} results in {round(time.time()-start_time, 2)} seconds")
    return candidate_tweets

def jaccard_similarity(a, b):
    x, y = set(a), set(b)
    return len(x&y) / len(x|y)

def score(row):
    if (row.len < 10 or row.len > 250 or
        row.trump or row.symbols > 2 or
        row.text[0] in punctuation or row.digits > 4 or
        wordfilter.blacklisted(row.text) or row.repeated_sentences):
        return 0
    return row.jaccard + row.self_similarity

def score_candidate_tweets(candidate_tweets):
    df = pd.DataFrame({
        'text': candidate_tweets,
        'len': list(map(len,candidate_tweets)),
        'digits': [sum(map(str.isdigit, s)) for s in candidate_tweets],
        'trump': [s.lower().count("trump") for s in candidate_tweets],
        'symbols': [sum(ord(c)>=128 or c=='@' for c in s) for s in candidate_tweets],
        'repeated_sentences': [sum(counter := Counter(map(str.strip, re.split(r"[.!?]", s))).values()) - len(counter) for s in candidate_tweets],
        'jaccard': [1-sum(jaccard_similarity(a,b) for b in [PROMPT_FLAVOR_1,PROMPT_FLAVOR_2,PROMPT_FLAVOR_3])/3 for a in candidate_tweets],
        'self_similarity': [len(set(s))/len(s) if len(s) else 1 for s in candidate_tweets],
    })

    df['score'] = df.apply(score, axis=1)
    df.sort_values(by='score', ascending=False, inplace=True)
    print(f"\nTop 10 candidate tweets by score\n{42*'-'}\n{df.head(10)}\n")

    return df

def choose_tweet_from_scored_candidates(df):
    filtered_df = df[(0.4 < df.score) & (df.score < 0.65)]
    if not filtered_df.empty:
        response = filtered_df.sample()
        print(f"Randomly selected response: {response}\n")
        return reponse

@retry(wait=wait_exponential(multiplier=1, min=1, max=60), stop=stop_after_attempt(5))
def tweet_reply(api, follower_tweet_id, tweet):
    return api.update_status(status=tweet,
                             in_reply_to_status_id=follower_tweet_id,
                             auto_populate_reply_metadata=True)

if __name__ == "__main__":
    df_processed_tweets = load_processed_tweets()

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    follower_tweets = get_latest_tweets_by_followers(api)

    # get first new, unprocessed tweet
    new_follower_tweet = next(filter(lambda x: int(x[0]) not in set(df_processed_tweets.prompt_tweet_id), follower_tweets), None)
    print(f"{new_follower_tweet=}")

    if not new_follower_tweet:
        print(42*'-' + '\nNo new, unprocessed tweets. Aborting!')
        sys.exit(0)

    ai = load_aitextgen()
    candidate_tweets = generate_candidate_tweets(ai, new_follower_tweet[1])
    df_scored_tweets = score_candidate_tweets(candidate_tweets)
    new_tweet = choose_tweet_from_scored_candidates(df_scored_tweets)
    print(f"{new_tweet=}")

    if not new_tweet:
        print(42*'-' + '\nFailed to generate viable candidates. Aborting!')
        sys.exit(0)

    status = tweet_reply(api, new_follower_tweet[0], new_tweet.text.item())

    # log tweet
    log_df = pd.DataFrame([[*new_tweet, status.id_str, new_tweet.text.item()]], columns=COLUMNS)
    log_df.to_csv(FILE_PATH, mode='a', header=not os.path.exists(FILE_PATH), index=False, encoding='utf-8')

    print(f"appended new row to {FILE_PATH}:\n{log_df}")
    print(42*'-' + '\nScript succeeded!')

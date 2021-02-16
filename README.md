## Overview
This repo uses the GPT-2 deep learning model (via [aitextgen](https://docs.aitextgen.io/)) to post on Twitter in the style of Donald Trump on this account: https://twitter.com/donaldtrumpbot5/with_replies

Specifically, every 10 minutes, a GitHub Actions workflow is triggered. This workflow executes `tweet.py`, which:
1. grabs the 10 newest tweet from every follower
2. picks an unprocessed tweet to use
3. feeds a prompt into `aitextgen` and generates 60 candidate responses
4. scores, ranks, then randomly chooses a candidate to tweet
5. logs tweet to the dataframe `processed.csv`

## How to run
Things you'll need to run this bot:
- A Twitter account
  - making a new account requires a phone number. You can use Google Voice
  - you'll need to [apply for developer access](https://developer.twitter.com/en/apply-for-access) to use the API
  - [create API credentials](https://developer.twitter.com/en/portal/dashboard) and save them for the next step
- Create four [repository secrets](https://docs.github.com/en/actions/reference/encrypted-secrets#creating-encrypted-secrets-for-a-repository) the script will grab as environment variables and pass to `tweepy` to communicate with the Twitter API
  - consumer_key
  - consumer_secret
  - access_token
  - access_token_secret

## Future work
#### Improve code quality
`script.py` is bearable now because it's short. Right?

#### Score better
The simple and janky candidate scoring system is very hard-coded, arbitrary, and doesn't work well at choosing the best Tweet. It currently:
1. filters out obviously bad candidates
	- tweets that are too short (tend to be uninteresting)
	- tweets that are too long
	- tweets with "Trump" (usually not in the first-person)
	- tweets with too many non-ASCII characters (usually URL's or hashtags unrelated to the tweet)
2. computes "prompt-similarity" and "self-similarity" using Jaccard similarity
	- many candidates just repeat the input prompt or repeat themselves and this is uninteresting
	- Jaccard similarity is a simple but inaccurate metric for prompt-similarity
3. uses the scores from step (2) to choose a random candidate
	- this often misses the most creative or on-topic candidate
	- short sentences generate higher scores because they repeat fewer words, and we exclude them because they are less interesting. This is a sign that the scoring needs tweaking

#### Extend run-time
While it would be possible to properly fine-tune the GPT-2 model on a dataset of Trump's writing, or run one of the larger GPT-2 models, or call out to and execute on Google Colab instead of the GitHub runner, or use a self-hosted runner, the [magic sauce](https://github.com/charlesjlee/trump_gpt2_bot/blob/main/tweet.py#L62-L66) for generating Tweets in the first-person voice of Trump is pretty effective. I think an easier improvement would be to scale up candidate generation and improve candidate scoring.

The Actions job currently runs for <3 minutes. This includes importing the "small" model in 13 seconds and generating 60 results in ~60 seconds. The majority of the time is actually taken up by installing dependencies at 1.5 minutes. However,
>[Each job in a workflow can run for up to 6 hours of execution time](https://docs.github.com/en/actions/reference/usage-limits-billing-and-administration#usage-limits)

At the current rate of 1 candidate per second, we could instead generate 21600 candidates per 6 hours. However, without a better scoring metric, we would just be selecting blindly from a large pool and may not see better results. Also, duplicate results could be a problem.

#### Some inputs fail to generate candidate result
This problem is sporadic, can be avoided by retrying, and is a bug in my code -- sometimes tweet candidates are empty. Example of a problematic input tweet:
```
'Over the last 10 days, I’ve taken action on:\n\n- COVID-19\n- The economy\n- Climate change\n- Racial equity\n- Immigration\n- Health care \n- LGBTQ+ rights\n\nAnd I’m just getting started.'
```

#### Vary the magic sauce
`prompt_updated` is primarily composed of three hard-coded Tweets by Trump and this causes responses to sometimes by very similar. See if I can vary the input Tweets.

#### Avoid large downloads
Each execution of the workflow downloads 1GB+ (776MB for PyTorch and 548MB for the GPT-2 "small" model). This is not really an issue on this public repo because execution is still very fast and isn't hitting any quotas, but it would be nice to take advantage of GitHub's support for [caching dependencies](https://docs.github.com/en/actions/guides/caching-dependencies-to-speed-up-workflows).

## Things that didn't help
#### Fine-tuning the GPT-2 small model on Trump's tweets
`aitextgen` gives a [_Hello World_ example](https://docs.aitextgen.io/tutorials/hello-world/) of fine-tuning on Shakespeare plays, but the results are terrible. This could be because the number of input tokens used is "64 vs. 1024 for base GPT-2". I don't know how much of a difference using fewer input tokens makes.

I used the _Hello World_ script to fine-tune on a [dataset of Trump's tweets](https://www.thetrumparchive.com/faq), but the results were unintelligible. Some of the spelling errors and punctuation mistakes are because I didn't properly sanitize the tweets, but the overall lack of coherent-ness confuses me. Perhaps this dataset is too small or the CPU-friendly configuration in _Hello World_ is incapable of producing good results.

<details>
<summary>sample output</summary>
<p>

```
Trump
In the winning you are losing from aport of the American Cuts
yourage and I am taking able to presidency the “They are the biggest World Summits Lowing the Senate
==========
Trump
Eman I will never have been forced the destrug nice
Watch me on this Country has destroying the fact that has done more exciting the party of the worst and in order to fight meeting of Con
==========
Trump
Thanks
You have the most I don t cheapable
I can be honeting information to be assidereds for the way to following the signed of the facts
There is a miss Unful in the greatest
==========
Trump signature
The Was a lands of New York Cont of Scott and I divately come back to the stands and the bigest friends of New Hampshire
Watch Macno ret
==========
Trump is the best tweeting
“@Pennsaso is a numbership
Great job at 4 00 P M on
Thanks General Greenborg
Congratulations Bethan
“There is the Georges Mem
==========
Trump
Thank you tomorrow in Minesean
My interview on to at 1 00 P M Enjoy
I will be in the missed at 7 30 PM views on LOVE
ISINTH DOU NEVER
==========
Trump
Thanks
This is apoloic for all of yourselfull failed renoot
I love it
There is the best high taxes to our country
Will be on my great honor to the IranianaVER
If
==========
Trump to the United People Great Erasternie Former
EVERE FAKE NEWS
EWSY chead of Trump Angelogy Scotland Getting for the Feduclear of s cele
==========
Trump Georgian Break Low Together
They has foreigned politicians are once
It s a great honor to run for president who has been in the history of Georgia who is standing the greatest and stain
```
</p>
</details>

#### Using different temperatures
`aitextgen`'s defines the _temperature_ parameter as:
>Determines the "creativity" of the generated text

and sets a default value of **0.7**. I experimented with different temperatures in `[0.6, 0.7, 0.8, 0.9, 1.0, 1.1]` and found **0.7** to give the most consistently good results. Lower temperatures tended to be "conservative" and repeat phrases. Higher temperatures produced mostly garbage with the occasional good result not being noticeably better than the good results produced by **0.7**.

## Misc stuff
Images used for Twitter profile
- https://commons.wikimedia.org/wiki/File:Donald_Trump_(39630669575).jpg
- https://commons.wikimedia.org/wiki/File:Donald_Trump_by_Gage_Skidmore_2.jpg
- https://commons.wikimedia.org/wiki/File:Donald_Trump_January_2016.jpg

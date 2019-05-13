import time
import requests
import requests.auth
import praw
from pandas import read_csv
from pandas import DataFrame
from pandas import concat

# Just Google 'What is my useragent' to get this
userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"

clientId = '-lHJ-Etm_dVLEg'
clientSecret = "6iNTXvVqkSRliLSpP0D9N-srTYQ"

username = 'RedditCommentLSTM'
password = "12345678"

idLogPath = "data/post_ids.csv"

def getPraw():
  return praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

def main():
    r = getPraw()
    page = r.subreddit('all')
    top_posts = page.hot(limit=10)
    all_ids = {}
    post_ids = []
    comment_ids = []
    current_time =  time.mktime(time.localtime())
    for post in top_posts:
        print(post.name)
        post_ids.append(post.id)
        single_post_comments = []
        for comment in post.comments.list():
            single_post_comments.append(tuple([comment.id, current_time]))
        comment_ids.append(single_post_comments)
    df = DataFrame({'Posts': post_ids, 'Comments': comment_ids}, columns= ['Posts', 'Comments'])
    export_csv = df.to_csv(idLogPath, index = None, header=True)


if __name__ == "__main__":
    main()

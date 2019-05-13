import time
import requests
import requests.auth
import praw

# Just Google 'What is my useragent' to get this
userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"

clientId = '-lHJ-Etm_dVLEg'
clientSecret = "6iNTXvVqkSRliLSpP0D9N-srTYQ"

username = 'RedditCommentLSTM'
password = "12345678"

def getPraw():
  return praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

def main():
    r = getPraw()
    page = r.subreddit('politics')
    top_posts = page.new(limit=25)
    for post in top_posts:
        for comment in post.comments.list():
            print(comment.author.name + "/" + str(comment.author.comment_karma) + "/" + str(comment.score) + "/" + comment.body)


if __name__ == "__main__":
    main()

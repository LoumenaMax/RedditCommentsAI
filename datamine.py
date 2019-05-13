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

postIdLogPath = "data/post_ids.csv"
commentIdLogPath= "data/comment_ids.csv"
commentDataPath= "data/comment_data.csv"

# Number of Posts we are going to track
postLimit = 10
# Totl number of comments we are going to track
# TODO: Speed up comment instantiation
maxComments = 25

def getPraw():
  return praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

def getTrackingData(posts):
    post_ids = []
    comment_ids = []
    current_time =  time.mktime(time.localtime())
    for post in posts:
        print(post.id)
        post_ids.append(post.id)
        for comment in post.comments.list():
            comment_ids.append(comment.id)
    return {'Posts': post_ids}, {'Comments': comment_ids, 'Time': current_time}

def exportTrackingData(postData, commentData):
    p_df = DataFrame(postData, columns= ['Posts'])
    c_df = DataFrame(commentData, columns=['Comments', 'Time'])
    export_csv_p = p_df.to_csv(postIdLogPath, index = None, header=True)
    export_csv_c = c_df.to_csv(commentIdLogPath, index = None, header=True)

def getCommentData(comments, posts, r):
    commentCount = 0
    commentData = []
    for index, row in posts.iterrows():
        submission = r.submission(row[0])
        for s_comment in submission.comments.list():
            print(s_comment.id)
            commentData.append([
                s_comment.score,
                s_comment.author.comment_karma,
                s_comment.created_utc,
                s_comment.edited,
                len(s_comment.replies)
            ])
            commentCount += 1
            if commentCount >= maxComments:
                break
        if commentCount >= maxComments:
            break
    return DataFrame(commentData, columns=['Score', 'Author Karma', 'Time Created', 'Edited', 'Replies'])

def getInstantiatedData(r):
    c_dataset = read_csv(commentIdLogPath)
    p_dataset = read_csv(postIdLogPath)
    getCommentData(c_dataset, p_dataset, r).to_csv(commentDataPath, index = None, header=True)

def main():
    r = getPraw()
    # page = r.subreddit('all')
    # posts = page.hot(limit=postLimit)
    # postData, commentData = getTrackingData(posts)
    #
    # exportTrackingData(postData, commentData)
    print(getInstantiatedData(r))


if __name__ == "__main__":
    main()

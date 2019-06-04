import time
import requests
import requests.auth
import praw
from pathlib import Path
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
commentDataPath= "data/comments/{}.csv"

# Time in seconds between time steps
interval = 600.0
# Number of Posts we are going to track
postLimit = 250
# Totl number of comments we are going to track
# TODO: Speed up comment instantiation
maxComments = 4000
full = False

def getPraw():
  return praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

def getTrackingData(posts):
    post_ids = []
    comment_ids = []
    for post in posts:
        print(post.id)
        post_ids.append(post.id)
    return {'Posts': post_ids}



def exportTrackingData(postData):
    p_df = DataFrame(postData, columns= ['Posts'])
    export_csv_p = p_df.to_csv(postIdLogPath, index = None, header=True)

def commentToString(r, comment, replies_len):
    submission_score = comment.submission.score
    parent_score = None
    if comment.parent_id != comment.link_id:
        # Has no parent comment
        return
    else:
        return
    return "{},{},{},{},{},{}\r\n".format(
        time.time(),
        s_comment.score,
        s_comment.author.comment_karma,
        s_comment.created_utc,
        s_comment.edited,
        replies_len
    )

def getSingleCommentData(s_comment, replies_len):
    id = s_comment.id
    if fileExists(id):
        appendToComment(commentToString(s_comment), id)
    else:
        comment_dFrame = DataFrame([[
            time.time(),
            s_comment.score,
            s_comment.author.comment_karma,
            s_comment.created_utc,
            s_comment.edited,
            replies_len
        ]], columns=['Time', 'Score', 'Author Karma', 'Time Created', 'Edited', 'Replies'])
        comment_dFrame.to_csv(commentDataPath.format(str(id)), index = None, header=True)

def getRepliesData(commentForest, r):
    if len(commentForest  <= 0)
        return
    for top_comment in commentForest:
        replies = top_comment.replies
        getSingleCommentData(top_comment, len(replies.list()))
        getRepliesData(top_comment.replies)

def getAllData(posts, r):
    commentCount = 0
    commentData = []
    for index, row in posts.iterrows():
        submission = r.submission(row[0])
        for top_comment in submission.comments:
            replies = top_comment.replies
            replies_len = len(replies.list())

            commentCount += 1
            commentCount += replies_len

            getSingleCommentData(top_comment, replies_len)
            getRepliesData(top_comment.replies)

            if commentCount >= maxComments:
                full = True
                return

def appendToComment(data, id):
    f = open(commentDataPath.format(str(id)), "a")
    f.write(data)
    f.close()

def fileExists(id):
    config = Path(commentDataPath.format(str(id)))
    return config.is_file()

def main():
    r = getPraw()

    page = r.subreddit('all')
    posts = page.new(limit=postLimit)
    postData = getTrackingData(posts)
    exportTrackingData(postData)

    starttime = time.time()
    while True:
        getAllData(posts, r)
        time.sleep(interval - ((time.time() - starttime) % interval))
        print(getInstantiatedData(r))



if __name__ == "__main__":
    main()

import time
import requests
import requests.auth
import praw
import os
import threading
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
finishedCommentPath= "data/finished/{}.csv"
commentDataFolderPath="data/comments"

# Time in seconds between time steps
interval = 600.0
# 12 hours in seconds
twelvehours = 60.0 * 60.0 * 12.0
# Number of Posts we are going to track
postLimit = 100
# Totl number of comments we are going to track
# TODO: Speed up comment instantiation
maxComments = 4000

def getPraw():
    return praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

def getTrackingData(posts):
    post_ids = []
    comment_ids = []
    for post in posts:
        post_ids.append(post.id)
    return {'Posts': post_ids}



def exportTrackingData(postData):
    p_df = DataFrame(postData, columns= ['Posts'])
    export_csv_p = p_df.to_csv(postIdLogPath, index = None, header=True)

def commentToString(s_comment, replies_len, parent_score, submission_score):
    return "{},{},{},{},{},{},{},{}\r\n".format(
        time.time(),
        s_comment.score,
        s_comment.author.comment_karma,
        s_comment.created_utc,
        s_comment.edited,
        replies_len,
        parent_score,
        submission_score
    )

def getSingleCommentData(s_comment, replies_len, parent_score, submission_score):
    id = s_comment.id
    if time.time() - s_comment.created_utc >= twelvehours:
        os.rename(commentDataPath.format(id), finishedCommentPath.format(id))
        return
    if fileExists(id):
        appendToComment(commentToString(s_comment, replies_len, parent_score, submission_score), id)
    else:
        comment_dFrame = DataFrame([[
            time.time(),
            s_comment.score,
            s_comment.author.comment_karma,
            s_comment.created_utc,
            s_comment.edited,
            replies_len,
            parent_score,
            submission_score
        ]], columns=['Time', 'Score', 'Author Karma', 'Time Created', 'Edited', 'Replies', 'Parent Score', 'Submission Score'])
        comment_dFrame.to_csv(commentDataPath.format(str(id)), index = None, header=True)

def getRepliesData(commentForest, parent_score, submission_score):
    if len(commentForest)  <= 0:
        return
    for top_comment in commentForest:
        replies = top_comment.replies
        getSingleCommentData(top_comment, len(replies.list()), parent_score, submission_score)
        getRepliesData(top_comment.replies, top_comment.score, submission_score)

def getAllData(posts, r):
    commentCount = 0
    threads = []
    full = False
    for submission in posts:
        if full:
            break
        submission_score = submission.score
        for top_comment in submission.comments:
            replies = top_comment.replies
            replies_len = len(replies.list())

            commentCount += 1
            commentCount += replies_len

            x = threading.Thread(target=threadTopComment, args=(top_comment, replies_len, submission_score,))
            x.start()
            threads.append(x)

            if commentCount >= maxComments:
                full = True
                break
    for thread in threads:
        thread.join()
    return full

def threadTopComment(top_comment, replies_len, submission_score):
    getSingleCommentData(top_comment, replies_len, None, submission_score)
    getRepliesData(top_comment.replies, top_comment.score, submission_score)

def getAllDataFull(r):
    directory = os.fsencode(commentDataFolderPath)
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        id, file_extension = os.path.splitext(filename)
        comment = r.comment(id)
        comment.refresh()
        parent_score = None
        submission_score = None
        if not comment.link_id == comment.parent_id:
            parent_score = comment.parent().score
        submission_score = comment.submission.score
        appendToComment(commentToString(comment, len(comment.replies.list()), parent_score, submission_score), id)

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

    # TODO: Find a way to save tracking data for posts
    # postData = getTrackingData(posts)
    # exportTrackingData(postData)
    starttime = time.time()
    full = False
    while True:
        begin_time = time.time()
        if time.time() - starttime >= twelvehours:
            full = True
        if not full:
            full = getAllData(posts, r)
        else:
            getAllDataFull(r)
        if time.time()-begin_time > 600:
            print("Took over 10 minutes to go through the data!")
            print("Consider lowering the \'postlimit\' variable or the \'maxComments\' variable")
            return
        print("Time taken: {}".format(time.time()-begin_time))
        time.sleep(interval - ((time.time() - starttime) % interval))



if __name__ == "__main__":
    main()

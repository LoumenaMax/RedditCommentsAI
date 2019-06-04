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
interval = 300.0
# 12 hours in seconds
twelvehours = 60.0 * 60.0 * 12.0
# Number of Posts we are going to track
postLimit = 200
# Totl number of comments we are going to track
# TODO: Speed up comment instantiation
maxComments = 1500
full = False
full_lock = threading.Lock()
commentCount = 0
commentCount_lock = threading.Lock()

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

def commentToString(s_comment, replies_len, parent_score, submission_score, submission_time, parent_time):
    return "{},{},{},{},{},{},{},{},{}\r\n".format(
        time.time(),
        s_comment.score,
        s_comment.author.comment_karma,
        s_comment.created_utc - submission_time,
        s_comment.created_utc - parent_time if parent_time else None,
        s_comment.edited,
        replies_len,
        parent_score,
        submission_score
    )

def getSingleCommentData(s_comment, replies_len, parent_score, submission_score, submission_time, parent_time):
    id = s_comment.id
    global commentCount
    if time.time() - s_comment.created_utc >= twelvehours:
        full = True
        os.rename(commentDataPath.format(id), finishedCommentPath.format(id))
        return
    if fileExists(id):
        if s_comment.author is None:
            os.remove(commentDataPath.format(id))
            commentCount_lock.acquire()
            try:
                commentCount -= 1
            finally:
                commentCount_lock.release()
        else:
            appendToComment(commentToString(s_comment, replies_len, parent_score, submission_score, submission_time, parent_time), id)
    else:
        if s_comment.author is not None:
            comment_dFrame = DataFrame([[
                time.time(),
                s_comment.score,
                s_comment.author.comment_karma,
                s_comment.created_utc - submission_time,
                s_comment.created_utc - parent_time if parent_time else None,
                s_comment.edited,
                replies_len,
                parent_score,
                submission_score
            ]], columns=['Time', 'Score', 'Author Karma', 'Time Since Submission Created', 'Time Since Parent Created', 'Edited', 'Replies', 'Parent Score', 'Submission Score'])
            comment_dFrame.to_csv(commentDataPath.format(str(id)), index = None, header=True)

def getRepliesData(commentForest, parent_score, submission_score, submission_time, parent_time):
    if len(commentForest)  <= 0:
        return
    for top_comment in commentForest:
        replies = top_comment.replies
        getSingleCommentData(top_comment, len(replies.list()), parent_score, submission_score, submission_time, parent_time)
        getRepliesData(top_comment.replies, top_comment.score, submission_score, submission_time, top_comment.created_utc)

def getAllData(r):
    threads = []
    post_data = read_csv(postIdLogPath)
    for index, row in post_data.iterrows():
        x = threading.Thread(target=threadSubmission, args=(row['Posts'], r,))
        x.start()
        threads.append(x)
    for thread in threads:
        thread.join()
    print(r.auth.limits)

def threadSubmission(submission_id, r):
    global commentCount
    global full
    finished = False
    submission = r.submission(submission_id)
    submission_score = submission.score
    submission_time = submission.created_utc
    for top_comment in submission.comments:
        replies = top_comment.replies
        replies_len = len(replies.list())

        commentCount_lock.acquire()
        try:
            if commentCount >= maxComments:
                finished = True
            else:
                commentCount += 1
                commentCount += replies_len
        finally:
            commentCount_lock.release()

        if finished:
            break

        getSingleCommentData(top_comment, replies_len, None, submission_score, submission_time, None)
        top_comment.replies.replace_more(limit=None)
        getRepliesData(top_comment.replies, top_comment.score, submission_score, submission_time, top_comment.created_utc)

        if commentCount >= maxComments:
            full = True
            break

def getAllDataFull(r):
    directory = os.fsencode(commentDataFolderPath)
    threads = []
    for file in os.listdir(directory):
        x = threading.Thread(target=threadFull, args=(file,r,))
        x.start()
        threads.append(x)
    for thread in threads:
        thread.join()

def threadFull(file, r):
    global commentCount
    filename = os.fsdecode(file)
    id, file_extension = os.path.splitext(filename)
    comment = r.comment(id)
    try:
        comment.refresh()
    except praw.exceptions.ClientException:
        os.remove(commentDataPath.format(id))
        commentCount_lock.acquire()
        try:
            commentCount -= 1
        finally:
            commentCount_lock.release()
            return
    parent_score = None
    submission_score = None
    parent_time = None
    if not comment.link_id == comment.parent_id:
        parent = comment.parent()
        parent_score = parent.score
        parent_time = parent.created_utc
    submission_score = comment.submission.score
    submission_time = comment.submission.created_utc
    appendToComment(commentToString(comment, len(comment.replies.list()), parent_score, submission_score, submission_time, parent_time), id)


def appendToComment(data, id):
    f = open(commentDataPath.format(str(id)), "a")
    f.write(data)
    f.close()

def fileExists(id):
    config = Path(commentDataPath.format(str(id)))
    return config.is_file()

def main():
    r = getPraw()
    global full
    global commentCount
    global maxComments
    
    print("----------------------------------------------")
    print("Time between intervals: {} min".format(interval/60))
    print("Tracking {} posts and {} comments for {} hours".format(postLimit, maxComments, (twelvehours/60)/60))
    print("----------------------------------------------")
    print("")
    page = r.subreddit('all')
    posts = page.new(limit=postLimit)

    postData = getTrackingData(posts)
    exportTrackingData(postData)

    starttime = time.time()
    while True:
        begin_time = time.time()
        if time.time() - starttime >= twelvehours:
            full = True
        if not full:
            getAllData(r)
        else:
            getAllDataFull(r)
        if time.time()-begin_time > interval:
            print("Took over {} minutes to go through the data!".format(interval/60))
            print("Consider lowering the \'postlimit\' variable or the \'maxComments\' variable")
            return
        print("Time taken: {}".format(time.time()-begin_time))
        print("Comment Count: {}/{}".format(str(commentCount), str(maxComments)))
        print("Time taken per comment: {}s".format((time.time()-begin_time)/commentCount))
        print("")
        time.sleep(interval - ((time.time() - starttime) % interval))

if __name__ == "__main__":
    main()

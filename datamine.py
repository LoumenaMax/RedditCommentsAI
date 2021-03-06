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

class CommentData:
    def __init__(self, comment, replies_len, parent_score, submission_score, submission_time, parent_time):
        self.comment = comment
        self.replies_len = replies_len
        self.parent_score = parent_score
        self.submission_score = submission_score
        self.time_from_submission = comment.created_utc - submission_time
        if parent_time:
            self.time_from_parent = comment.created_utc - parent_time
        else:
            self.time_from_parent = None

# Just Google 'What is my useragent' to get this
userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"

clientId = '-lHJ-Etm_dVLEg'
clientSecret = "6iNTXvVqkSRliLSpP0D9N-srTYQ"

username = 'RedditCommentLSTM'
password = "12345678"

postIdLogPath = "data/post_ids4.csv"
commentIdLogPath= "data/comment_ids.csv"
finishedFolderPath= "data/finished"
commentDataFolderPath="data/comments4"
commentDataPath= commentDataFolderPath + "/{}.csv"
finishedCommentPath= finishedFolderPath + "/{}.csv"

# Time in seconds between time steps
interval = 300.0
# 12 hours in seconds
twelvehours = 60.0 * 60.0 * 12.0
# Number of Posts we are going to track
postLimit = 200
# Totl number of comments we are going to track
# TODO: Speed up comment instantiation
maxComments = 400
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

def commentToString(commentData):
    return "{},{},{},{},{},{},{},{},{}\r\n".format(
        time.time(),
        commentData.comment.score,
        commentData.comment.author.comment_karma,
        commentData.time_from_submission,
        commentData.time_from_parent if commentData.time_from_parent else "",
        commentData.comment.edited,
        commentData.replies_len,
        commentData.parent_score if commentData.parent_score else "",
        commentData.submission_score
    )

def deleteComment(id):
    global commentCount
    os.remove(commentDataPath.format(id))
    commentCount_lock.acquire()
    try:
        commentCount -= 1
    finally:
        commentCount_lock.release()

def getSingleCommentData(commentData):
    id = commentData.comment.id
    global commentCount
    if time.time() - commentData.comment.created_utc >= twelvehours:
        full = True
        os.rename(commentDataPath.format(id), finishedCommentPath.format(id))
        return
    if fileExists(id):
        if commentData.comment.author is None:
            deleteComment(id)
        else:
            appendToComment(commentToString(commentData), id)
    else:
        if commentData.comment.author is not None:
            commentCount_lock.acquire()
            try:
                commentCount += 1
            finally:
                commentCount_lock.release()
            comment_dFrame = DataFrame([[
                time.time(),
                commentData.comment.score,
                commentData.comment.author.comment_karma,
                commentData.time_from_submission,
                commentData.time_from_parent,
                commentData.comment.edited,
                commentData.replies_len,
                commentData.parent_score,
                commentData.submission_score
            ]], columns=['Time', 'Score', 'Author Karma', 'Time Since Submission Created', 'Time Since Parent Created', 'Edited', 'Replies', 'Parent Score', 'Submission Score'])
            comment_dFrame.to_csv(commentDataPath.format(str(id)), index = None, header=True)

def getRepliesData(commentForest, parent_score, submission_score, submission_time, parent_time):
    if len(commentForest)  <= 0:
        return
    for top_comment in commentForest:
        replies = top_comment.replies
        getSingleCommentData(CommentData(top_comment, len(replies.list()), parent_score, submission_score, submission_time, parent_time))
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
            finished = commentCount >= maxComments
        finally:
            commentCount_lock.release()

        if finished:
            break

        getSingleCommentData(CommentData(top_comment, replies_len, None, submission_score, submission_time, None))
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
    filename = os.fsdecode(file)
    id, file_extension = os.path.splitext(filename)
    comment = r.comment(id)
    try:
        comment.refresh()
    except praw.exceptions.ClientException:
        deleteComment(id)
        return
    parent_score = None
    submission_score = None
    parent_time = None
    if time.time() - comment.created_utc >= twelvehours:
        os.rename(commentDataPath.format(id), finishedCommentPath.format(id))
        return
    if not comment.link_id == comment.parent_id:
        parent = comment.parent()
        parent_score = parent.score
        parent_time = parent.created_utc
    if comment.author is None:
        deleteComment(id)
    else:
        submission_score = comment.submission.score
        submission_time = comment.submission.created_utc
        appendToComment(commentToString(CommentData(comment, len(comment.replies.list()), parent_score, submission_score, submission_time, parent_time)), id)


def appendToComment(data, id):
    f = open(commentDataPath.format(str(id)), "a")
    f.write(data)
    f.close()

def fileExists(id):
    config = Path(commentDataPath.format(str(id)))
    return config.is_file()

def clearCommentsFolder():
    directory = os.fsencode(commentDataFolderPath)
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        id, file_extension = os.path.splitext(filename)
        os.remove(commentDataPath.format(id))

def setupFolders():
    if not os.path.isdir(commentDataFolderPath):
        os.mkdir(commentDataFolderPath)
    if not os.path.isdir(finishedFolderPath):
        os.mkdir(finishedFolderPath)
    clearCommentsFolder()



def main():
    r = getPraw()
    setupFolders()
    global full
    global commentCount
    global maxComments

    print("----------------------------------------------")
    print("Started at: {}".format(time.asctime(time.localtime())))
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
        time_elapsed = begin_time-starttime
        if time.time() - starttime >= twelvehours:
            full = True
        if time_elapsed > 600 and commentCount == 0:
            break
        if not full:
            getAllData(r)
        else:
            getAllDataFull(r)
        if time.time()-begin_time > interval:
            print("Took over {} minutes to go through the data!".format(interval/60))
            print("Consider lowering the \'postlimit\' variable or the \'maxComments\' variable")
            return
        print("Total Time Elapsed: {} min".format(time_elapsed/60))
        print("Time taken: {}".format(time.time()-begin_time))
        print("Comment Count: {}/{}".format(str(commentCount), str(maxComments)))
        print("Completed Count: {}".format(len(os.listdir(os.fsencode(finishedFolderPath)))))
        print("Comments are full" if full else "Comments are still being pulled")
        if commentCount > 0:
            print("Time taken per comment: {}s".format((time.time()-begin_time)/commentCount))
        if not len(os.listdir(os.fsencode(commentDataFolderPath))) == commentCount:
            print("Problem with commentCount! Count Value is {} but real value is {}!".format(commentCount, len(os.listdir(os.fsencode(commentDataFolderPath)))))
        print("")
        if time_elapsed > ((twelvehours * 2) + 300):
            break
        time.sleep(interval - ((time.time() - starttime) % interval))

if __name__ == "__main__":
    main()

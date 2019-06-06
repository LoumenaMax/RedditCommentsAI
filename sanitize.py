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

userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36"

clientId = '-lHJ-Etm_dVLEg'
clientSecret = "6iNTXvVqkSRliLSpP0D9N-srTYQ"

username = 'RedditCommentLSTM'
password = "12345678"

finishedFolderPath= "data/finished"
finishedCommentPath= finishedFolderPath + "/{}.csv"

#1559769866.8480306

def getPraw():
    return praw.Reddit(user_agent=userAgent, client_id=clientId, client_secret=clientSecret)

def getFinishedFiles():
    directory = os.fsencode(finishedFolderPath)
    return os.listdir(directory)

def exportDataFrame(dataframe, id):
    dataframe.to_csv(finishedCommentPath.format(id), index = None, header=True)

def readDataFrame(id):
    return read_csv(finishedCommentPath.format(id))

def deleteRowsAfterTwelveHours(dataframe):
    #144 because 5min intervals * 12 is 1 hr * 12 is 12 hours
    return dataframe.iloc[0:144,]

def threadAddSubscribersAndNSFW(df, id, r):
    subreddit = None
    try:
        subreddit = r.comment(id).submission.subreddit
    except:
        print("Problem in loading subreddit from comment {}.".format(str(id)))
    subscribers = [subreddit.subscribers] * 144
    nsfw = [subreddit.over18] * 144
    df['Subreddit Subscribers'] = subscribers
    df['Subreddit NSFW'] = nsfw
    exportDataFrame(df, id)

def main():
    r = getPraw()
    threads = []
    for file in getFinishedFiles():
        filename = os.fsdecode(file)
        id, file_extension = os.path.splitext(filename)
        df = readDataFrame(id)
        df = deleteRowsAfterTwelveHours(df)
        x = threading.Thread(target=threadAddSubscribersAndNSFW, args=(df,id,r,))
        x.start()
        threads.append(x)
    for thread in threads:
        thread.join()


if __name__ == "__main__":
    main()

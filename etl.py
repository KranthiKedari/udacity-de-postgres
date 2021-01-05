import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *

def process_song_file(cur, filepath):
    """
    - Processes song file.
    - Extracts the song information and artist information.
    - inserts the song data and artist data into the songs and artists tables.
    """
    # open song file
    df = pd.read_json(filepath, lines = True)

    # insert song record
    song_data = df[["song_id", "title", "artist_id", "year", "duration"]].values[0].tolist()
    cur.execute(song_table_insert, song_data)
    
    # insert artist record
    artist_data = df[["artist_id", "artist_name", "artist_location", "artist_latitude", "artist_longitude"]].values[0].tolist()
    cur.execute(artist_table_insert, artist_data)

def process_log_file(cur, filepath):
    """
    - Processes a log file and reads the json data in the file.
    - Filters the records with page as NextSong
    - Create a time record based on the timestamp.
    - Queries for song id and artist id if exists and
    - Adds a songplay record in the songplay table
    """
    # open log file
    df = pd.read_json(filepath, lines = True)

    # filter by NextSong action
    df = df[df['page'] == 'NextSong']

    # convert timestamp column to datetime
    t = df[["ts"]].apply(pd.to_datetime) 
    
    # insert time data records
    time_data = list(zip(df["ts"], t["ts"].dt.hour, t["ts"].dt.day, t["ts"].dt.week, t["ts"].dt.month, t["ts"].dt.year, t["ts"].dt.weekday))
    column_labels = ('start_time', 'hour', 'day', 'week', 'month', 'year', 'weekday')
    time_df = pd.DataFrame(data = time_data, columns = column_labels)

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[["userId", "firstName", "lastName", "gender", "level"]].drop_duplicates(subset=['userId'])

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        ts = row["ts"]
        time_data = time_df[time_df["start_time"]== ts]
        # insert songplay record
        songplay_data = (time_data["start_time"].values[0].item(), int(row["userId"]), row["level"], songid, artistid, int(row["sessionId"]), row["location"], row["userAgent"])
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    - Recursively looks through a directory and 
    - Processes the files using the function that is passed.
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()

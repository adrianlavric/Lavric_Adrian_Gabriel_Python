"""
SongStorage Application

This module provides functionality for managing a music library. Users can add,
delete, modify, search, play songs and create save lists based on criteria.

Features:
- Add songs to the storage and metadata to the database by path.
- Delete songs and their metadata by their ID.
- Modify metadata for existing songs.
- Search for songs based on criteria.
- Create a save list archive of songs based on criteria.
- Play songs using pygame library.

Usage:
1. Run the script.
2. Use commands to customize your song library(type 'help' to see the available ones).
3. Type `quit` to exit the application.

Dependencies:
- PostgreSQL for the database(psql).
- Python modules: pg8000, os, shutil, datetime, zipfile, pygame, time
(use: 'pip install pg8000' and 'pip install pygame' if needed).

Author: Lavric Adrian-Gabriel 3A3, Facultatea de Informatica Iasi, UAIC
Date: 7.01.2025
"""

import pg8000 # For connecting to the PostgreSQL database
import os # For working with files
import shutil # For copying files
from datetime import datetime # For handling date formatting
import zipfile # For creating the archive
import pygame # For playing songs
import time # For handling rewinding/forwarding songs

#Database setup
USER = "postgres" #: Database user name
PASSWORD = "postgres" #: Database user password
HOST = "localhost" #: Database host name
DB = "songstorage" #: Database name

#Valid song extensions
SONG_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".aiff", ".mp4"}

#SQL query for table set up
table_setup_query = """
CREATE TABLE IF NOT EXISTS songs (
    id SERIAL PRIMARY KEY,           -- id of each song
    file_name VARCHAR(255) NOT NULL, -- path of the song
    artist VARCHAR(255) NOT NULL,    -- name of the artist
    song_name VARCHAR(255) NOT NULL, -- name of the song
    release_date DATE,               -- release date of the song
    tags TEXT[]                      -- list of tags of the song
);
"""


def database_setup():
    """
    This method sets up the 'songstorage' PostgreSQL database. It connects to the
    'postgres' database and checks if 'songstorage' exists and connects to it, if
    it does not, it creates it, and creates the 'songs' table.

    Handles any errors that may occur during interacting with the database.

    Returns:
        None
    """

    try:
        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database="postgres")
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'songstorage'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE DATABASE songstorage")
            print("Database 'songstorage' was created.")
        else:
            print("Database 'songstorage' exists.")
        cursor.close()
        conn.close()

        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()
        cursor.execute(table_setup_query)
        print("Table 'songs' was created.")
        conn.commit()
        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'song_storage' error: {e}")


def create_folder():
    """
    This method creates the folder 'Storage' if it does not exist.
    If the folder already exists, it specifies it.

    Handles any errors that may occur during folder creation.

    Returns:
        None
    """

    folder_path = "Storage"
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print("Storage folder created.")
        else:
            print("Storage folder exists.")
    except OSError as e:
        print(f"Error creating folder '{folder_path}': {e}")


def add_song(song_path, artist, song_name, release_date, tags):
    """
    This method adds a song to the 'Storage' folder and its metadata to the database.
    It validates the given path is a valid song with one of the supported extensions,
    check the release date format, and the other args to not be NULL. Then, if these
    requirements are met, it copies the song file to the 'Storage' folder and inserts
    the metdata into the 'songs' table in the 'songstorage' database, returning the id.
    It also logs success and error messages to the console.

    Args:
        song_path (str): The path of the file.
        artist (str): The name of the artist.
        song_name (str): The name of the song.
        release_date (str): The release date as 'YYYY-MM-DD'.
        tags (str list): A list of tags associated with the song.

    Handles any errors that may occur during interacting with the database and any other
    error that occur during the adding process.

    Returns:
        None(it only prints the id of the song inserted into the 'songs' table)
    """

    try:
        if not os.path.isfile(song_path):
            print("Error: The file does not exist or is a directory.")
            return
        if not os.path.splitext(song_path)[1].lower() in SONG_EXTENSIONS:
            print("Error: The file is not a valid song.")
            return
        try:
            datetime.strptime(release_date, "%Y-%m-%d")
        except ValueError:
            print("Error: Invalid date format.")
            return
        if not artist or not song_name:
            print("Error: Missing artist or song name.")
            return
        if not tags or all(tag.strip() == "" for tag in tags):
            print("Error: Missing tags.")
            return

        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()

        storage_path = os.path.join("Storage", os.path.basename(song_path))
        if not os.path.exists(storage_path):
            shutil.copy(song_path, storage_path)
            print(f"Song '{song_path}' was added to storage.")

        cursor.execute(
            """INSERT INTO songs (file_name, artist, song_name, release_date, tags) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (os.path.basename(song_path), artist, song_name, release_date, tags)
        )
        song_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Song {song_id} was added to storage.")

        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'songstorage' error: {e}")
    except Exception as e:
        print(f"Error adding song: {e}")


def delete_song(song_id):
    """
    This method deletes a song from both the 'Storage' folder and its metadata from
    the database. It retrieves the file name from the 'Songs' table by using the id,
    deletes the song with the specified path from the 'Storage' folder if it exists
    and then removes the metadata from the database 'songstorage'.
    It also logs success and error messages to the console.

    Args:
        song_id (int): The ID of the song to be deleted.

    Handles any errors that may occur during interacting with the database and any other
    error that occur during the deletion process.

    Returns:
        None
    """

    try:
        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()

        cursor.execute("SELECT file_name FROM songs WHERE id = %s", (song_id,))
        result = cursor.fetchone()
        if not result:
            print(f"Error: There is no song with ID {song_id}.")
            return

        file_name = result[0]
        song_path = os.path.join("Storage", file_name)

        if os.path.exists(song_path):
            os.remove(song_path)
            print(f"Song '{file_name}' was deleted.")
        else:
            print(f"Error: Song '{file_name}' not found.")

        cursor.execute("DELETE FROM songs WHERE id = %s", (song_id,))
        conn.commit()
        print(f"Song {song_id} was deleted.")

        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'songstorage' error: {e}")
    except Exception as e:
        print(f"Error deleting song: {e}")


def modify_data(song_id):
    """
    This method modifies the metadata of a song in the database 'songstorage'.
    It retrieves the current song data from the 'Songs' table by the song ID and
    allows the user to insert new values or to keep the same values if Enter is
    pressed. Then, it updates the song metadata in the database 'songstorage'.
    It also logs success and error messages to the console.

    Args:
        song_id (int): The ID of the song to be modified.

    Handles any errors that may occur during interacting with the database and any other
    error that occur during the modifying process.

    Returns:
        None
    """

    try:
        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM songs WHERE id = %s", (song_id,))
        result = cursor.fetchone()
        if not result:
            print(f"Error: There is no song with ID {song_id}.")
            return

        print("Enter new value or press enter to not modify:")
        artist = input(f"Artist [{result[2]}]: ").strip() or result[2]
        song_name = input(f"Song Name [{result[3]}]: ").strip() or result[3]
        release_date = input(f"Release Date [{result[4]}]: ").strip() or result[4]
        try:
            if release_date and release_date != result[4]:
                datetime.strptime(release_date, "%Y-%m-%d")
        except ValueError:
            print("Error: Invalid date format.")
            return
        tags_input = input(f"Tags separated by ',' [{', '.join(result[5])}]: ").strip()
        tags = tags_input.split(',') if tags_input else result[5]

        cursor.execute(
            """UPDATE songs SET artist = %s, song_name = %s, release_date = %s, tags = %s WHERE id = %s""",
            (artist, song_name, release_date, tags, song_id)
        )
        conn.commit()
        print(f"Song {song_id} was updated.")

        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'songstorage' error: {e}")
    except Exception as e:
        print(f"Error modifying song data: {e}")


def search(criteria):
    """
    This method searches for songs in the database 'songstorage' based on specified
    criteria. It allows searching for songs that match the specified fields given by
    key to the specified values, each criterion being comma-separated in the format
    'key=value' and it supports case-insensitive search using 'ILIKE'.
    It also logs success and error messages to the console.

    Args:
        criteria (str): Comma-separated criteria, e.g. "artist=Queen, tags=rap".

    Handles any errors that may occur during interacting with the database and any other
    error that occur during the search process.

    Returns:
        None
    """

    try:
        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()

        query = "SELECT * FROM songs WHERE "
        params = []
        conditions = []

        for criterion in criteria.split(','):
            key, value = map(str.strip, criterion.split('='))
            if key.lower() == "artist":
                conditions.append("artist ILIKE %s")
                params.append(f"%{value}%")
            elif key.lower() == "song_name":
                conditions.append("song_name ILIKE %s")
                params.append(f"%{value}%")
            elif key.lower() == "release_date":
                conditions.append("release_date = %s")
                params.append(value)
            elif key.lower() == "tags":
                conditions.append("%s = ANY(tags)")
                params.append(value)
            elif key.lower() == "file_name":
                conditions.append("file_name ILIKE %s")
                params.append(f"%{value}%")
            else:
                print(f"Error: Invalid criterion '{key}'.")

        if conditions:
            query += " AND ".join(conditions)
        else:
            print("Error: Invalid criteria.")
            return

        cursor.execute(query, params)
        results = cursor.fetchall()

        if results:
            print(f"Results found - {len(results)}:")
            for row in results:
                print(
                    f"ID: {row[0]}, File_name: {row[1]}, Artist: {row[2]},"
                    f" Song_name: {row[3]}, Release_date: {row[4]}, Tags: {', '.join(row[5])}"
                )
        else:
            print("Error: No song found.")

        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'songstorage' error: {e}")
    except Exception as e:
        print(f"Error searching for song: {e}")


def create_save_list(archive_path, criteria):
    """
    This method creates a ZIP archive containing songs that match the search criteria.
    It retrieves songs based on the criteria and saves them to a ZIP archive created at
    the specified path. The function supports the same searching style as the 'search'
    method and the archive is created if at least one song is found.
    It also logs success and error messages to the console.

    Args:
        archive_path (str): The path of the ZIP archive creation.
        criteria (str): Comma-separated criteria, e.g. "artist=Queen, tags=rap".

    Handles any errors that may occur during interacting with the database and any other
    error that occur during the archive creation process.

    Returns:
        None
    """

    try:
        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()

        query = "SELECT file_name FROM songs WHERE "
        params = []
        conditions = []

        for criterion in criteria.split(','):
            key, value = map(str.strip, criterion.split('='))
            if key.lower() == "artist":
                conditions.append("artist ILIKE %s")
                params.append(f"%{value}%")
            elif key.lower() == "song_name":
                conditions.append("song_name ILIKE %s")
                params.append(f"%{value}%")
            elif key.lower() == "release_date":
                conditions.append("release_date = %s")
                params.append(value)
            elif key.lower() == "tags":
                conditions.append("%s = ANY(tags)")
                params.append(value)
            elif key.lower() == "file_name":
                conditions.append("file_name ILIKE %s")
                params.append(f"%{value}%")
            else:
                print(f"Error: Invalid criterion '{key}'.")

        if conditions:
            query += " AND ".join(conditions)
        else:
            print("Error: Invalid criteria.")
            return

        cursor.execute(query, params)
        results = cursor.fetchall()

        if results:
            with zipfile.ZipFile(archive_path, 'w') as zipf:
                for row in results:
                    file_name = row[0]
                    file_path = os.path.join("Storage", file_name)
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=file_name)
                        print(f"Song '{file_name}' was added to archive.")
                    else:
                        print(f"Error: There is no song {file_name}.")

            print(f"Archive '{archive_path}' was created.")
        else:
            print("Error: No song found.")

        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'songstorage' error: {e}")
    except Exception as e:
        print(f"Error creating save_list: {e}")


def play_song(song_id):
    """
    This method plays the song with the ID given by retrieving the file name from the
    database 'songstorage' using `pygame`. It also allows the user to rewind or forward
    the song by 10 seconds using left and right arrow keys and to stop the playback
    using the ESC key.
    It also logs success and error messages to the console.

    Args:
        song_id (int): The ID of the song to be played.

    Handles any errors that may occur during interacting with the database and any other
    error that occur during the song playback process.

    Returns:
        None
    """

    try:
        conn = pg8000.connect(user=USER, password=PASSWORD, host=HOST, database=DB)
        cursor = conn.cursor()

        cursor.execute("SELECT file_name FROM songs WHERE id = %s", (song_id,))
        result = cursor.fetchone()
        if not result:
            print(f"Error: There is no song with ID {song_id}.")
            return

        file_name = result[0]
        song_path = os.path.join("Storage", file_name)

        if os.path.exists(song_path):
            pygame.init()
            window_size = (700, 350)
            pygame.display.set_mode(window_size)
            pygame.display.set_caption(f"{file_name}")

            pygame.mixer.init()
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()

            song_length = pygame.mixer.Sound(song_path).get_length()
            print(f"Playing '{file_name}'. Press left/right arrow keys to rewind/forward and ESC to stop.")

            start_time = time.time()
            running = True
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.KEYDOWN:
                        passed_time = (time.time() - start_time) + pygame.mixer.music.get_pos() / 1000.0
                        if event.key == pygame.K_LEFT:
                            rewind_to = max(0, passed_time - 10)
                            pygame.mixer.music.stop()
                            pygame.mixer.music.play(start=rewind_to)
                            start_time = time.time() - rewind_to
                        elif event.key == pygame.K_RIGHT:
                            forward_to = passed_time + 10
                            if forward_to >= song_length:
                                print("Song finished playing.")
                                pygame.mixer.music.stop()
                                running = False
                            else:
                                pygame.mixer.music.stop()
                                pygame.mixer.music.play(start=forward_to)
                                start_time = time.time() - forward_to
                        elif event.key == pygame.K_ESCAPE:
                            pygame.mixer.music.stop()
                            print("Song stopped playing.")
                            running = False
                pygame.time.wait(100)

            pygame.quit()
        else:
            print(f"Error: There is no song {file_name}.")

        cursor.close()
        conn.close()

    except pg8000.dbapi.DatabaseError as e:
        print(f"Database 'songstorage' error: {e}")
    except Exception as e:
        print(f"Error playing song: {e}")


def main():
    """
    Main method for the SongStorage application.
    This method sets up the database and storage folder, then provides an interactive loop
    where the user can manage their music library by adding, deleting, modifying, searching,
    playing songs and creating save lists by typing different commands.

    Commands:
        - help: Display the list of available commands.
        - add_song: Add a song to the storage and its metadata to the database.
        - delete_song: Delete a song and its metadata using its ID.
        - modify_data: Modify metadata for a song using its ID.
        - search: Search for songs based on criteria (e.g. "artist=Queen, tags=rap").
        - create_save_list: Create an archive of songs based on specified criteria.
        - play: Play a song using its ID.
        - quit: Exit the application.

    Returns:
        None
    """

    database_setup()
    create_folder()

    print("SongStorage: type 'help' to see the available commands.")
    command = ""
    while command.lower().strip() != "quit":
        command = input("Enter command: ").lower().strip()
        if command == "help":
            print("Available commands:\n"
                  "- Add_song <path> <metadata>\n"
                  "- Delete_song <id>\n"
                  "- Modify_data <id>\n"
                  "- Search <criteria>\n"
                  "- Create_save_list <criteria>\n"
                  "- Play <id>\n"
                  "- Quit")
        elif command == "add_song":
            song_path = input("Enter path: ").strip()
            artist = input("Enter artist: ").strip()
            song_name = input("Enter song name: ").strip()
            release_date = input("Enter release date <YYYY-MM-DD>: ").strip()
            tags = input("Enter tags separated by ',': ").strip().split(',')
            add_song(song_path, artist, song_name, release_date, tags)
        elif command == "delete_song":
            song_id = input("Enter song ID: ").strip()
            if song_id.isdigit():
                delete_song(int(song_id))
            else:
                print("Error: Invalid ID.")
        elif command == "modify_data":
            song_id = input("Enter song ID: ").strip()
            if song_id.isdigit():
                modify_data(int(song_id))
            else:
                print("Error: Invalid ID.")
        elif command == "search":
            criteria = input("Enter search criteria (e.g., artist=Kanye, song_name=Wolves): ").strip()
            search(criteria)
        elif command == "create_save_list":
            archive_path = input("Enter archive path: ").strip()
            criteria = input("Enter search criteria (e.g., artist=Kanye, song_name=Wolves): ").strip()
            create_save_list(archive_path, criteria)
        elif command == "play":
            song_id = input("Enter song ID: ").strip()
            if song_id.isdigit():
                play_song(int(song_id))
            else:
                print("Error: Invalid ID.")
        elif command != "quit" :
            print("Error: Invalid command, type 'help'.")


if __name__ == "__main__":
    """
    Script entry point for SongStorage.
    It ensures the main function runs when the script is executed
    """
    main()



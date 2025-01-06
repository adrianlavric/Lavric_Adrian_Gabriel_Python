import pg8000
import os
import shutil
from datetime import datetime

USER = "postgres"
PASSWORD = "postgres"
HOST = "localhost"
DB = "songstorage"

SONG_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".aiff", ".mp4"}

table_setup_query = """
CREATE TABLE IF NOT EXISTS songs (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NOT NULL,
    song_name VARCHAR(255) NOT NULL,
    release_date DATE,
    tags TEXT[]
);
"""


def database_setup():
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
    folder_path = "Storage"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Storage folder created.")
    else:
        print(f"Storage folder exists.")


def add_song(song_path, artist, song_name, release_date, tags):
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

def main():
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
        elif command != "quit" :
            print("Error: Invalid command, type 'help'.")


if __name__ == "__main__":
    main()



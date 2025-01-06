import pg8000
import os

USER = "postgres"
PASSWORD = "postgres"
HOST = "localhost"
DB = "songstorage"

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
        print(f"Error setting up database 'song_storage': {e}")


def create_folder():
    folder_path = "Storage"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Storage folder created.")
    else:
        print(f"Storage folder exists.")


def main():
    database_setup()
    create_folder()


if __name__ == "__main__":
    main()



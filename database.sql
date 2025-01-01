CREATE DATABASE songstorage;

CREATE TABLE songs (
    id SERIAL PRIMARY KEY,         
    file_name VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NOT NULL,  
    song_name VARCHAR(255) NOT NULL,
    release_date DATE,              
    tags TEXT[]                  
);


drop table if exists notification;
drop table if exists likes;
drop table if exists interested_in_city;
drop table if exists profile;
drop table if exists users;
drop table if exists city;


CREATE TABLE city (
city_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
city_name VARCHAR(100) NOT NULL
);

CREATE TABLE users (
id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
user_login VARCHAR(50) UNIQUE,
is_admin BOOLEAN DEFAULT FALSE,
user_password VARCHAR(128)
);

CREATE TABLE profile (
profile_id INTEGER REFERENCES users(id),
first_name VARCHAR(128) NOT NULL,
second_name VARCHAR(128) NOT NULL,
city_id INT NOT NULL,
gender_name VARCHAR(10) NOT NULL,
preferred_gender VARCHAR(10) NOT NULL,
profile_img VARCHAR(120) DEFAULT 'duck.png',
biography TEXT DEFAULT 'I am nobody',
vk_inst VARCHAR(120) NOT NULL,
min_age INT NOT NULL,
max_age INT NOT NULL,
age INT NOT NULL,
FOREIGN KEY(city_id) REFERENCES city(city_id),
PRIMARY KEY(profile_id)
);

CREATE TABLE interested_in_city (
city_id INT NOT NULL,
user_id INT NOT NULL,
FOREIGN KEY(city_id) REFERENCES city(city_id),
FOREIGN KEY(user_id) REFERENCES users(id),
PRIMARY KEY(city_id, user_id)
);

CREATE TABLE likes (
liker_id INTEGER REFERENCES users(id),
liked_id INTEGER REFERENCES users(id),
PRIMARY KEY (liker_id, liked_id)
);

CREATE TABLE notification (
notification_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
administrator_id INTEGER NOT NULL REFERENCES users(id),
user_id INTEGER NOT NULL REFERENCES users(id),
reason TEXT NOT NULL,
notification_date TIMESTAMP NOT NULL
);


INSERT INTO city (city_name)
VALUES ('москва'), ('санкт-петербург'), ('рязань');

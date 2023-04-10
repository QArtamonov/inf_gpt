import datetime
import sqlite3


conn = sqlite3.connect('bot_database.db')
c = conn.cursor()


async def create_tables():
    # Drop "users" table
    c.execute("DROP TABLE IF EXISTS users")

    # Drop "rounds" table
    c.execute("DROP TABLE IF EXISTS rounds")

    # Drop "photos" table
    c.execute("DROP TABLE IF EXISTS photos")

    # Create "users" table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        nickname TEXT,
        comment TEXT,
        voice INTEGER DEFAULT 0,
        password TEXT,
        count_users INTEGER,
        count_rounds INTEGER,
        date_time INTEGER DEFAULT 0
    )
    ''')

    # Create "rounds" table
    c.execute('''
    CREATE TABLE IF NOT EXISTS rounds (
        rounds_number INTEGER PRIMARY KEY,
        rounds_name TEXT
    )
    ''')

    # Create "photos" table
    c.execute('''
    CREATE TABLE IF NOT EXISTS photos (
        chat_id INTEGER,
        photo_id TEXT,
        likes INTEGER DEFAULT 0,
        rounds_number INTEGER,
        winner INTEGER DEFAULT 0,
        FOREIGN KEY (chat_id) REFERENCES users(chat_id),
        FOREIGN KEY (rounds_number) REFERENCES rounds(rounds_number)
    )
    ''')

    conn.commit()


async def add_admin(chat_id, password, count_rounds, count_users):
    c.execute('''
    INSERT INTO users (chat_id, password, count_rounds, count_users)
    VALUES (?, ?, ?, ?)
    ''', (chat_id, password, count_rounds, count_users))
    conn.commit()


async def check_password(password):
    c.execute('''
    SELECT password FROM users
    ''')
    result = c.fetchall()
    for res in result:
        if res[0] == password:
            return True
    return False


async def add_chat_id(chat_id):
    c.execute('''
    INSERT INTO users (chat_id)
    VALUES (?)
    ''', (chat_id,))
    conn.commit()


async def add_user_nickname(chat_id, nickname):
    c.execute('''
    UPDATE users
    SET nickname=?
    WHERE chat_id=?
    ''', (nickname, chat_id))
    conn.commit()


async def check_number_of_users():
    c.execute('''
    SELECT count(nickname) FROM users
    ''')
    count_nicknames = c.fetchone()[0]
    c.execute('''
    SELECT sum(count_users) FROM users
    ''')
    sum_count_users = c.fetchone()[0]
    return count_nicknames == sum_count_users


async def get_chat_ids():

    c.execute("SELECT chat_id FROM users")
    chat_ids = [row[0] for row in c.fetchall()]
    return chat_ids


async def write_rounds_to_db(rounds):

    for i, round in enumerate(rounds):
        c.execute("INSERT INTO rounds (rounds_number, rounds_name) VALUES (?,?)", (i + 1, round))

    conn.commit()


async def get_round_info(round_number, round_name):

    # Get the total number of rounds from the database
    c.execute("SELECT COUNT(*) FROM rounds")
    total_rounds = c.fetchone()[0]

    # Return the result as a formatted string
    result = "<b>Раунд {} из {}\nПодбери подходящее фото к заголовку:</b>\n\n<em>{}</em>".format(round_number, total_rounds, round_name)

    return result


async def write_photo_to_database(chat_id, photo_id, round_number):

    c.execute(
        "INSERT INTO photos (chat_id, photo_id, rounds_number) VALUES (?, ?, ?)",
        (chat_id, photo_id, round_number),
    )

    conn.commit()


async def all_photos_submitted(round_number):

    # Get the number of photos submitted for the current round
    c.execute("SELECT COUNT(photo_id) FROM photos WHERE rounds_number = ?", (round_number,))
    photos_submitted = c.fetchone()[0]

    # Get the total number of users
    c.execute("SELECT MAX(count_users) FROM users")
    total_users = c.fetchone()[0]

    # Compare the number of photos submitted with the total number of users
    print(photos_submitted, total_users)
    return photos_submitted == total_users


async def get_rounds_from_db():

    c.execute("SELECT MAX(count_rounds) FROM users")
    result = c.fetchone()

    return result[0]


async def send_album_with_inline_voting_buttons(round_number, chat_id):
    c.execute("SELECT photo_id FROM photos WHERE rounds_number = ? and chat_id != ?", (round_number, chat_id))
    photo_ids = c.fetchall()
    photo_ids = [photo_id[0] for photo_id in photo_ids]
    print('БД send_album_with_inline_voting_buttons', photo_ids)
    return photo_ids


async def update_likes_in_photo_table(photo_id, round_number):

    c.execute("UPDATE photos SET likes = (likes + 1) WHERE photo_id = ? and rounds_number = ?", (str(photo_id), str(round_number)))
    conn.commit()


async def increment_voices_in_user_table(chat_id):

    c.execute(f"UPDATE users SET voice = (voice + 1) WHERE chat_id = '{chat_id}'")
    conn.commit()


async def compare_votes_with_participants(round_number):

    c.execute("SELECT COUNT(voice) FROM users WHERE voice = ?", (round_number,))
    result = c.fetchone()
    total_votes = result[0]

    c.execute("SELECT COUNT(*) FROM users")
    result = c.fetchone()
    total_participants = result[0]

    return total_votes == total_participants



async def extract_photo_id(callback_data, round_number, chat_id):
    i = int(callback_data.split('_')[1])
    photo_ids = await send_album_with_inline_voting_buttons(round_number, chat_id)
    print("extract_photo_id + i", photo_ids, i)
    return photo_ids[i-1]


async def get_round_name(round_number):

    c.execute("SELECT rounds_name FROM rounds WHERE rounds_number = ?", (round_number,))
    round_name = c.fetchone()[0]

    return round_name


async def get_game_results():

    # Get the number of likes for each user
    c.execute("""
        SELECT users.nickname, SUM(photos.likes)
        FROM users
        JOIN photos ON users.chat_id = photos.chat_id
        GROUP BY users.chat_id
    """)
    results = c.fetchall()

    # Get the maximum number of likes
    max_likes = max([result[1] for result in results])

    # Get the winners and other participants
    winners = []
    others = []
    for result in results:
        if result[1] == max_likes:
            winners.append(result[0])
        else:
            others.append(result[0])

    # Create the results string
    results_string = "Победитель игры:\n\n"
    for winner in winners:
        results_string += f"🤳 {winner}, {max_likes} likes\n"

    results_string += "\nОстальные участники:\n\n"
    for other in others:
        c.execute("""
            SELECT SUM(photos.likes)
            FROM photos
            WHERE photos.chat_id = (
                SELECT chat_id
                FROM users
                WHERE nickname = ?
            )
        """, (other,))
        likes = c.fetchone()[0]
        results_string += f"{other}, {likes} likes\n"

    return results_string


async def update_winners_in_photo_table(round_number):
    # Get the maximum number of likes for the round
    c.execute("""
        SELECT MAX(likes) as max_likes
        FROM photos
        WHERE rounds_number = ?
    """, (round_number,))
    max_likes = c.fetchone()[0]

    # Update the winner column for all photos with the maximum number of likes
    c.execute("""
        UPDATE photos
        SET winner = (winner + 1)
        WHERE rounds_number = ? AND likes = ?
    """, (round_number, max_likes))

    conn.commit()


async def get_winning_photos_info():
    c.execute("""
        SELECT p.photo_id, p.rounds_number, r.rounds_name, u.nickname
        FROM photos p
        JOIN users u ON p.chat_id = u.chat_id
        JOIN rounds r ON p.rounds_number = r.rounds_number
        WHERE p.winner = 1
    """)
    result = c.fetchall()

    return result


async def write_datetime_to_database(chat_id, time):

    c.execute(f"UPDATE users SET date_time='{time}' WHERE chat_id={chat_id}")

    conn.commit()


async def check_time(chat_id, time, round):

    c.execute(f"SELECT date_time FROM users ORDER BY date_time DESC")
    exp_time = c.fetchone()[0]
    print(exp_time)
    exp_time = exp_time.split('.')[0]
    print(exp_time)
    exp_time_m = exp_time.split(':')[1]
    print(exp_time_m)
    exp_time_s = exp_time.split(':')[2]
    print(exp_time_s)
    exp_time = datetime.timedelta(minutes=int(exp_time_m), seconds=int(exp_time_s))
    print(exp_time, type(exp_time))
    # exp_time = datetime.time.strftime(exp_time, '%H:%M:%S')
    time = str(time).split('.')[0]
    time_m = time.split(':')[1]
    time_s = time.split(':')[2]
    time = datetime.timedelta(minutes=int(time_m), seconds=int(time_s))
    print('ЭТАЛОННАЯ ДАТА', exp_time)
    print('АКТУАЛЬНАЯ ДАТА', time)
    print('ЭТАЛОННАЯ ДАТА', type(exp_time))
    print('АКТУАЛЬНАЯ ДАТА', type(time))
    result = time - exp_time
    print('РЕЗУЛЬТАТ ВЫЧИТАНИЯ', result)
    result = int(str(result).split(':')[1])

    if result >= 1:
        print('Убираем лайк')
        c.execute(f"UPDATE photos SET likes=(likes-1) WHERE chat_id={chat_id} and rounds_number={round}")
        conn.commit()
        return False

    conn.commit()
    return True







from flask import Flask, render_template, url_for, request, flash, session, redirect
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT

UPLOAD_FOLDER = 'static/uploads/'

app = Flask(__name__)
app.secret_key = 'pobeda'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

try:
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
except:
    print('no connection')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        user_login = request.form['username']
        password = request.form['password']
        cursor.execute('SELECT * FROM users WHERE user_login = %s', (user_login,))
        account = cursor.fetchone()
        if account:
            password_rs = account['user_password']
            # If account exists in users table in out database
            if check_password_hash(password_rs, password):
                # Create session data, we can access this data in other routes
                if user_login in admins_logins():
                    session['adminin'] = True
                session['loggedin'] = True
                session['user_login'] = account['user_login']
                user_id = account['id']
                session['user_id'] = user_id
                cursor.execute('SELECT * FROM profile WHERE profile_id = %s', (user_id,))
                user_profile = cursor.fetchone()
                if user_profile:
                # Redirect to home page
                    return redirect(url_for('home_page'))
                else:
                    return redirect(url_for('profile_creating'))
            else:
                # Account doesnt exist or username/password incorrect
                flash('Incorrect username/password')
        else:
            # Account doesnt exist or username/password incorrect
            flash('Incorrect username/password')

    elif request.method == 'POST':
        flash('Please fill out the form!')

    return render_template('login.html')


@app.route('/new_profile', methods=['GET', 'POST'])
def profile_creating():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST' and 'submit' in request.form:
        cities = request.form.getlist('citySelect[]')
        if 'gender' not in request.form or 'pref_gender' not in request.form:
            flash('Choose gender!', category='error')
        elif not cities:
            flash('Choose preferred city(-ies)!', category='error')
        else:
            gender = request.form['gender']
            pref_gender = request.form['pref_gender']
            user_name = request.form['name']
            last_name = request.form['last_name']
            city = request.form['city']
            link = request.form['link']
            min_age = request.form['min_age']
            max_age = request.form['max_age']
            age = request.form['age']

            if not match_word(user_name) or not match_word(last_name) or not match_word(city):
                flash('Only ru and en characters!', category='error')
            elif not match_number(min_age) or not match_number(max_age) or not match_number(age):
                flash('Only numbers!', category='error')
            else:
                city = city.lower()
                cursor.execute("SELECT city_id FROM city WHERE city_name=%s", (city, ))
                city_id = cursor.fetchone()
                if not city_id:
                    cursor.execute(
                        "INSERT INTO city (city_name) "
                        "VALUES (%s) RETURNING city_id",
                        (city, ))
                    city_id = cursor.fetchone()
                    conn.commit()

                for pref_city in cities:
                    cursor.execute("SELECT city_id FROM city WHERE city_name=%s", (pref_city,))
                    pref_city_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO interested_in_city (city_id, user_id) "
                        "VALUES (%s, %s)",
                        (pref_city_id, session['user_id']))
                    conn.commit()

                cursor.execute(
                    "INSERT INTO profile (profile_id, first_name, second_name, gender_name, "
                    "preferred_gender, city_id, vk_inst, min_age, max_age, age) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (session['user_id'], user_name, last_name, gender,
                     pref_gender, city_id[0], link, min_age, max_age, age))
                conn.commit()
                return redirect(url_for('bio_and_photo'))

    cursor.execute("SELECT city_name FROM city")
    cities = cursor.fetchall()
    return render_template('new_profile.html', cities=cities)


@app.route('/bio_and_photo', methods=['GET', 'POST'])
def bio_and_photo():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        photo = request.files['file']
        if photo:
            if not allowed_file(photo.filename):
                flash('Allowed image types are - png, jpg, jpeg, gif', category='error')
            else:
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                print('upload_image filename: ' + filename)
                cursor.execute(
                    "UPDATE profile SET profile_img  = %s WHERE profile_id = %s  ",
                    (filename, session['user_id']))
                conn.commit()
        biography = request.form['biography']
        if biography:
            cursor.execute(
                "UPDATE profile SET biography = %s WHERE profile_id = %s  ",
                (biography, session['user_id']))
            conn.commit()
        return redirect(url_for('home_page'))
    return render_template('bio_photo.html')


@app.route('/notification/<int:id>', methods=['GET', 'POST'])
def notification(id):
    if 'adminin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST' and 'submit' in request.form:
        reason = request.form['reason']
        cursor.execute(
            "INSERT INTO notification (administrator_id, user_id, "
            "reason, notification_date) VALUES (%s, %s, %s, LOCALTIMESTAMP)  ",
            (session['user_id'], id, reason))
        conn.commit()
        return redirect(url_for('all_users'))

    return render_template('create_notification.html', id=id)


@app.route('/edit_page', methods=['GET', 'POST'])
def edit():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST' and 'submit' in request.form:
        if request.form.get('name'):
            name = request.form['name']
            cursor.execute(
                "UPDATE profile SET first_name  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()
        if request.form.get('last_name'):
            name = request.form['last_name']
            cursor.execute(
                "UPDATE profile SET second_name  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()
        if request.form.get('age'):
            name = request.form['age']
            cursor.execute(
                "UPDATE profile SET age  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()
        if request.form.get('vk_inst'):
            name = request.form['vk_inst']
            cursor.execute(
                "UPDATE profile SET vk_inst  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()
        if request.form.get('min_age'):
            name = request.form['min_age']
            cursor.execute(
                "UPDATE profile SET min_age  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()
        if request.form.get('max_age'):
            name = request.form['max_age']
            cursor.execute(
                "UPDATE profile SET max_age  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()

        if request.form.get('biography'):
            name = request.form['biography']
            cursor.execute(
                "UPDATE profile SET biography  = %s WHERE profile_id = %s  ",
                (name, session['user_id']))
            conn.commit()
        photo = request.files['file']
        if photo:
            if allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute(
                    "UPDATE profile SET profile_img  = %s WHERE profile_id = %s  ",
                    (filename, session['user_id']))
                conn.commit()
        if request.form.get('city'):
            city = request.form['city']
            city = city.lower()
            cursor.execute("SELECT city_id FROM city WHERE city_name=%s", (city,))
            city_id = cursor.fetchone()
            if not city_id:
                cursor.execute(
                    "INSERT INTO city (city_name) "
                    "VALUES (%s) RETURNING city_id",
                    (city,))
                city_id = cursor.fetchone()
                conn.commit()
            cursor.execute(
                "UPDATE profile SET city_id  = %s WHERE profile_id = %s  ",
                (city_id[0], session['user_id']))
            conn.commit()
        cities = request.form.getlist('citySelect[]')
        if cities:
            cursor.execute("DELETE FROM interested_in_city WHERE user_id=%s", (session['user_id'],))
            conn.commit()
            for pref_city in cities:
                cursor.execute("SELECT city_id FROM city WHERE city_name=%s", (pref_city,))
                pref_city_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO interested_in_city (city_id, user_id) "
                    "VALUES (%s, %s)",
                    (pref_city_id, session['user_id']))
                conn.commit()
        return redirect(url_for('home_page'))

    if request.method == 'POST' and 'delete' in request.form:
        return redirect(url_for('are_u_sure'))

    cursor.execute("SELECT city_name FROM city")
    all_cities = cursor.fetchall()
    return render_template('edit_page.html', profile_image=session['photo'],
                           name=session['first_name'], last_name=session['second_name'], age=session['age'], gender=session['gender_name'],
                           biography=session['biography'], vk_inst=session['vk_inst'], min_age=session['min_age'],
                           max_age=session['max_age'], city=session['city'], pref_gender=session['preferred_gender'], pref_cities=session['pref_cities'],
                          all_cities=all_cities)


@app.route('/delete_profile', methods=['GET', 'POST'])
def are_u_sure():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        if 'yes' in request.form:
            cursor.execute("DELETE FROM notification WHERE user_id=%s", (session['user_id'],))
            conn.commit()
            cursor.execute("DELETE FROM likes WHERE liker_id=%s OR liked_id=%s", (session['user_id'],session['user_id']))
            conn.commit()
            cursor.execute("DELETE FROM interested_in_city WHERE user_id=%s", (session['user_id'],))
            conn.commit()
            cursor.execute("DELETE FROM profile WHERE profile_id=%s", (session['user_id'],))
            conn.commit()
            cursor.execute("DELETE FROM users WHERE id=%s", (session['user_id'],))
            conn.commit()
            return redirect(url_for('login'))
        if 'no' in request.form:
            return redirect(url_for('edit'))
    return render_template('delete_profile.html')


@app.route('/home_page')
def home_page():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT is_admin FROM users WHERE id = %s", (session['user_id'],))
    is_admin = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM profile WHERE profile_id = %s", (session['user_id'],))
    account = cursor.fetchone()
    name = account['first_name']
    session['first_name'] = name
    last_name = account['second_name']
    session['second_name'] = last_name
    age = account['age']
    session['age'] = age
    gender = account['gender_name']
    session['gender_name'] = gender
    pref_gender = account['preferred_gender']
    session['preferred_gender'] = pref_gender
    biography = account['biography']
    session['biography'] = biography
    vk_inst = account['vk_inst']
    session['vk_inst'] = vk_inst
    min_age = account['min_age']
    session['min_age'] = min_age
    max_age = account['max_age']
    session['max_age'] = max_age
    image = account['profile_img']
    photo = 'static/uploads/'
    if image:
         photo += image
    else:
        photo += 'duck.png'
    session['photo'] = photo
    cursor.execute("SELECT city_name from city WHERE city_id = %s", (account['city_id'], ))
    city = cursor.fetchone()[0]
    session['city'] = city
    cursor.execute("SELECT city_id from interested_in_city WHERE user_id = %s", (session['user_id'], ))
    pref_cities = cursor.fetchall()
    pref_cities_name = []
    for pref_city in pref_cities:
        cursor.execute("SELECT city_name from city WHERE city_id = %s", (pref_city[0],))
        pref_cities_name.append(cursor.fetchone()[0])
    session['pref_cities'] = pref_cities_name
    cursor.execute("SELECT COUNT(*) from likes WHERE liked_id = %s", (session['user_id'],))
    count_of_likes = cursor.fetchone()[0]
    cursor.execute("SELECT * from notification WHERE user_id = %s", (session['user_id'],))
    warning = cursor.fetchone()
    return render_template('home_page.html', profile_image=photo,
                           name=name, last_name=last_name, age=age, gender=gender,
                           biography=biography, vk_inst=vk_inst, min_age=min_age,
                           max_age=max_age, city=city, pref_gender=pref_gender,
                           pref_cities_name=pref_cities_name,
                           likes=count_of_likes, is_admin=is_admin, warning=warning)


def match_word(word):
   return re.match(r'[A-Za-zА-Яа-я\s]+', word)


def match_number(number):
   return re.match(r'[0-9\s]+', number)


@app.route('/all_users', methods=['GET', 'POST'])
def all_users():
    if 'adminin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM profile")
    users = cursor.fetchall()
    return render_template('all_users.html', users=users)


@app.route('/seenotifications', methods=['GET', 'POST'])
def see_notifications():
    if 'adminin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM notification WHERE administrator_id = %s",
                   (session['user_id'],))
    my_notifications = cursor.fetchall()
    cursor.execute("SELECT id FROM users WHERE id != %s AND is_admin = %s",
                   (session['user_id'], True))
    admins_id = cursor.fetchall()
    other_notifications = []
    for id in admins_id:
        cursor.execute("SELECT * FROM notification WHERE administrator_id = %s",
                       (id[0],))
        notifs = cursor.fetchall()
        if notifs:
            for notif in notifs:
                other_notifications.append(notif)

    return render_template('all_notifications.html', my_notifications=my_notifications,
                           other_notifications=other_notifications)


@app.route('/user_profile_for_admin/<int:id>', methods=['GET', 'POST'])
def user_profile_for_admin(id):
    if 'adminin' not in session:
        return redirect(url_for('login'))
    profile_id = id
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM profile WHERE profile_id = %s",
                   (profile_id,))
    account = cursor.fetchone()
    name = account['first_name']
    second_name = account['second_name']
    vk_inst = account['vk_inst']
    age = account['age']
    gender = account['gender_name']
    biography = account['biography']
    image = account['profile_img']
    cursor.execute("SELECT city_name from city WHERE city_id = %s", (account['city_id'],))
    city = cursor.fetchone()[0]
    photo = 'static/uploads/'
    if image:
        photo += image
    else:
        photo += 'duck.png'

    return render_template('user_profile_for_admin.html', profile_image=photo,
                           name=name, second_name=second_name, vk_inst=vk_inst,
                           age=age, gender=gender,
                           biography=biography, city=city, profile_id=profile_id
                          )


@app.route('/delete_user_profile_admin/<int:id>', methods=['GET', 'POST'])
def delete_user_profile_admin(id):
    if 'adminin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        if 'yes' in request.form:
            cursor.execute("DELETE FROM notification WHERE user_id=%s", (id,))
            conn.commit()
            cursor.execute("DELETE FROM likes WHERE liker_id=%s OR liked_id=%s",
                           (id, id))
            conn.commit()
            cursor.execute("DELETE FROM interested_in_city WHERE user_id=%s", (id,))
            conn.commit()
            cursor.execute("DELETE FROM profile WHERE profile_id=%s", (id,))
            conn.commit()
            cursor.execute("DELETE FROM users WHERE id=%s", (id,))
            conn.commit()
            return redirect(url_for('all_users'))
        if 'no' in request.form:
            return redirect(url_for('user_profile_for_admin', id=id))
    return render_template('delete_user_profile_admin.html')


@app.route('/like/<int:id>')
def like(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT * FROM likes WHERE liker_id = %s AND liked_id = %s ",
        (session['user_id'], id))
    is_liked = cursor.fetchone()
    if is_liked is None:
        cursor.execute(
            "INSERT INTO likes (liker_id, liked_id) "
            "VALUES (%s, %s)",
            (session['user_id'], id))
        conn.commit()
    return redirect(url_for('user_profile'))


@app.route('/like_liker_profile/<int:id>')
def like_liker_profile(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT * FROM likes WHERE liker_id = %s AND liked_id = %s ",
        (session['user_id'], id))
    is_liked = cursor.fetchone()
    if is_liked is None:
        cursor.execute(
            "INSERT INTO likes (liker_id, liked_id) "
            "VALUES (%s, %s)",
            (session['user_id'], id))
        conn.commit()
    else:
        flash('You are already liked this profile!', category='error')
    return redirect(url_for('liker_profile', id=id))


@app.route('/user_likes')
def user_likes():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT liker_id FROM likes WHERE liked_id = %s"
                    , (session['user_id'], ))
    likers = cursor.fetchall()
    for i in range(len(likers)):
        cursor.execute("SELECT first_name FROM profile WHERE profile_id = %s"
                       , (likers[i][0],))
        liker_name = cursor.fetchone()[0]
        likers[i].append(liker_name)
    return render_template('likes.html', names=likers)


@app.route('/liker_profile/<int:id>')
def liker_profile(id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    profile_id = id
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM profile WHERE profile_id = %s",
                   (profile_id, ))
    account = cursor.fetchone()
    name = account['first_name']
    second_name = account['second_name']
    vk_inst = account['vk_inst']
    age = account['age']
    gender = account['gender_name']
    biography = account['biography']
    image = account['profile_img']
    cursor.execute("SELECT city_name from city WHERE city_id = %s", (account['city_id'],))
    city = cursor.fetchone()[0]
    photo = 'static/uploads/'
    if image:
        photo += image
    else:
        photo += 'duck.png'
    cursor.execute(
        "SELECT * FROM likes WHERE liker_id = %s AND liked_id = %s ",
        (session['user_id'], id))
    is_liked = cursor.fetchone()
    if is_liked is None:
        is_liked = False
    else:
        is_liked = True
    return render_template('liker_profile.html', profile_image=photo,
                           name=name, second_name=second_name, vk_inst=vk_inst,
                           age=age, gender=gender,
                           biography=biography, city=city, profile_id=profile_id,
                           is_liked=is_liked)


@app.route('/love')
def user_profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM profile WHERE age >= %s AND age <= %s AND gender_name = %s AND profile_id != %s AND "
                   "city_id "
                   "IN (SELECT city_id FROM interested_in_city WHERE user_id = %s) ORDER BY RANDOM() LIMIT 1"
                   , (session['min_age'], session['max_age'], session['preferred_gender'], session['user_id'], session['user_id']))
    account = cursor.fetchone()
    if account is None:
        return render_template('nobody.html')
    else:
        name = account['first_name']
        age = account['age']
        gender = account['gender_name']
        biography = account['biography']
        image = account['profile_img']
        cursor.execute("SELECT city_name from city WHERE city_id = %s", (account['city_id'],))
        city = cursor.fetchone()[0]
        photo = 'static/uploads/'
        profile_id = account['profile_id']
        if image:
            photo += image
        else:
            photo += 'duck.png'
    return render_template('user_profile.html', profile_image=photo,
                           name=name, age=age, gender=gender,
                           biography=biography, city=city, profile_id=profile_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        user_login = request.form['username']
        password = request.form['password']
        _hashed_password = generate_password_hash(password)
        cursor.execute('SELECT * FROM users WHERE user_login = %s', (user_login,))
        account = cursor.fetchone()
        if account:
            flash('Account already exists!')
        elif not re.match(r'[A-Za-z0-9]+', user_login):
            flash('Username must contain only characters and numbers!')
        elif not user_login or not password:
            flash('Please fill out the form!')
        else:
            # Account don't exist and the form data is valid, now insert new account into users table
            cursor.execute("INSERT INTO users (user_login, user_password) VALUES (%s,%s)",
                           (user_login, _hashed_password))
            conn.commit()
            if user_login in admins_logins():
                cursor.execute("UPDATE users SET is_admin = %s",
                               (True, ))
                conn.commit()
            return redirect(url_for('login'))

    elif request.method == 'POST':
        flash('Please fill out the form!')

    return render_template('register.html')


def admins_logins():
    return ['admin', 'admin1', 'admin2', 'admin3', 'moderator']


@app.route('/logout')
def logout():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)

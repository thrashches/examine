from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from mysql_db import MySQL
import mysql.connector as connector
from paginator import paginate
from sqlalchemy.orm import Session, joinedload
from sqlalchemy_filters import apply_filters
from models import engine, Films, Genres, Posters, Reviews, Users, Roles
from werkzeug.utils import secure_filename
import os
import hashlib
#from flaskext.markdown import Markdown
import random
from utils import add_filter
from jinja_markdown import MarkdownExtension




login_manager = LoginManager()
UPLOAD_FOLDER = 'media/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)
application = app

app.jinja_env.add_extension(MarkdownExtension)

app.config.from_pyfile('config.py')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.debug = True


@app.route('/posters/<filename>')
def posters(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title='404'), 404


mysql = MySQL(app)

login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пройдите аутентицикацию, чтобы получить доступ к этой странице.'
login_manager.login_message_category = 'warning'




class User(UserMixin):
    def __init__(self, user_id, login):
        super().__init__()
        self.id = user_id
        self.login = login


@login_manager.user_loader   
def load_user(user_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM users WHERE id = %s;', (user_id,))
    db_user = cursor.fetchone()
    cursor.close()
    if db_user:
        return User(user_id=db_user.id, login=db_user.login)
    return None    


def load_roles():
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT id, name FROM roles;')
    roles = cursor.fetchall()
    cursor.close()
    return roles
  

@app.route('/old_index')
def index():
    return render_template('index.html')


@app.route('/')
def films():
    session = Session(engine)
    user = current_user
    if current_user.is_authenticated:
        user = session.query(Users).get(current_user.id)
    context = {
        'genres': session.query(Genres).all(),
        'years': [int(i[0]) for i in session.query(Films.year).distinct()],
        'search_request': {
            'name': '',
            'genres': [],
            'year': [],
            'country': '',
            'length_from': '',
            'length_to': ''
        }
    }
    print(request.args.to_dict())
    query = session.query(Films)
    films = query.all()

    # Set default page number to 1 if page does not exist in request.args
    page = 1
    if request.args:
        search_request = request.args.to_dict()
        if 'page' in search_request.keys():
            page = int(search_request['page'])
            del search_request['page']
        context['search_request'] = request.args.to_dict()

        context['search_request']['genres'] = [int(g) for g in request.args.getlist('genres')]
        context['search_request']['year'] = [int(y) for y in request.args.getlist('year')]

        # If filter_query is none, all films will be shown
        filtered_query = None
        for key in context['search_request']:
            if context['search_request'][key]:
                if key == 'name':
                    filter_spec = [{'field': key, 'op': 'ilike', 'value': '%' + context['search_request'][key] + '%'}]
                    print(filter_spec)
                    filtered_query = add_filter(filtered_query, query, filter_spec)
                elif key == 'genres':
                    for val in context['search_request'][key]:
                        filter_spec = [{'field': 'genres', 'op': 'in', 'value': val}]
                        print(filter_spec)
                    if filtered_query is not None:
                        filtered_query = filtered_query.filter(Films.genres_collection.any(
                                    Genres.id.in_(context['search_request'][key])))
                    else:
                        filtered_query = query.filter(Films.genres_collection.any(
                                    Genres.id.in_(context['search_request'][key])))

                # Check all request args and it to query
                elif key == 'year':
                    filter_spec = [{'field': key, 'op': 'in', 'value': context['search_request'][key]}]
                    print(filter_spec)
                    filtered_query = add_filter(filtered_query, query, filter_spec)
                elif key == 'country':
                    filter_spec = [{'field': key, 'op': 'ilike', 'value': '%' + context['search_request'][key] + '%'}]
                    print(filter_spec)
                    filtered_query = add_filter(filtered_query, query, filter_spec)
                elif key == 'length_from':
                    filter_spec = [{'field': 'length', 'op': '>=', 'value': context['search_request'][key]}]
                    print(filter_spec)
                    filtered_query = add_filter(filtered_query, query, filter_spec)
                elif key == 'length_to':
                    filter_spec = [{'field': 'length', 'op': '<=', 'value': context['search_request'][key]}]
                    print(filter_spec)
                    filtered_query = add_filter(filtered_query, query, filter_spec)
                if filtered_query is not None:
                    films = filtered_query.all()
    # Search DEBUG
    print('films: {}'.format([f.name for f in films]))
    # Paginate results
    page_obj = paginate(films, 10, page)

    return render_template('films/index.html', page_obj=page_obj, context=context, page=page, user=user)


@app.route('/films/<int:film_id>')
def view_film(film_id):
    film = []
    poster = []
    user_review = []
    session = Session(engine)
    # Load film and poster
    try:
        film = session.query(Films).get(film_id)
        poster = session.query(Posters).filter(Posters.id == film.poster_id).one()

    # FIXME: Fix markdown output and user check
    except:
        abort(404)
    # Load user review
    try:
        user_review = session.query(Reviews).filter(Reviews.user_id == current_user.id,
                                                    Reviews.film_id == film_id).one()
    except:

        user_review = {}

    # Load other reviews
    try:
        other_reviews = session.query(Reviews).filter(Reviews.user_id != current_user.id,
                                                      Reviews.film_id == film_id).all()
    except:
        other_reviews = {}

    return render_template('films/show.html', film=film, poster=poster,
                           user_review=user_review, other_reviews=other_reviews)


@app.route('/films/<int:film_id>/remove')
@login_required
def remove_film(film_id):
    session = Session(engine)
    # Check if poster belongs to multiple films
    film = session.query(Films).get(film_id)
    # poster = session.query(Posters).filter(Posters.id == film.poster_id)
    other = session.query(Films).filter(Films.poster_id == film.poster_id).all()
    print('Films with same posters: {}'.format(len(other)))

    if len(other) == 1:  # If poster belongs only to this film
        poster = session.query(Posters).get(film.poster_id)
        file = poster.file_name
        path = os.path.join(app.config['UPLOAD_FOLDER'], file)
        # Remove poster instance
        session.delete(poster)

        # Remove poster file
        os.remove(path)
        print('Poster has been deleted: {}'.format(file))

    # Remove film instance and commit changes
    session.delete(film)
    session.commit()
    return redirect(url_for('films'))


@app.route('/films/<int:film_id>/add_review', methods=['GET', 'POST'])
@login_required
def add_review(film_id):
    if request.method == 'POST':
        # Getting review data from form
        form = request.form
        session = Session(engine)
        # Creating query
        new_review = Reviews(film_id=film_id, user_id=current_user.id, score=form['score'], text=form['text'])
        session.add(new_review)
        # Saving new review
        session.commit()
        return redirect(url_for('view_film', film_id=film_id))
    return render_template('films/add_review.html')


@app.route('/films/new', methods=['GET', 'POST'])
@login_required
def new_film():
    context = {'film': ''}

    if request.method == "GET":
        session = Session(engine)
        genres = session.query(Genres).all()
        context = {
            'genres': genres,
            'film': ''
        }
        session.close()
    # TODO: Make bleach check
    if request.method == 'POST':
        form = request.form
        print(request.files)
        if 'poster' not in request.files:
            flash('Постер не загружен')
            return redirect(request.url)
        file = request.files['poster']
        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            session = Session(engine)
            mime_type = file.content_type
            # Add random string to file, to prevent russian letters corrupt by secure_filename
            file_name = str(random.randint(10000, 99999)) + secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            file.save(path)
            with open(path, 'rb') as f:
                md5_hash = hashlib.md5(f.read()).hexdigest()

            poster = session.query(Posters).filter(Posters.md5_hash == md5_hash)
            poster_id = 0
            # FIXME: !!! FILE IS EMPTY AFTER WRITE !!! Fixed.
            # Duplicate posters check
            if len(poster.all()):
                poster_id = poster.first().id
                print('{}: poster exists'.format(poster_id))
                print(poster_id)
                # Remove file if exists
                os.remove(path)
            else:
                new_poster = Posters(file_name=file_name, mime_type=mime_type, md5_hash=md5_hash)
                session.add(new_poster)
                session.commit()

                poster_id = new_poster.id

                session.close()

            session = Session(engine)

            new_film = Films(name=form['name'], year=form['year'], country=form['country'], director=form['director'],
                             screenwriter=form['screenwriter'], actors=form['actors'], length=form['length'],
                             description=form['description'], poster_id=poster_id)

            session.add(new_film)
            session.commit()
            film = new_film.id

            session.close()
            if form.getlist('genres'):
                for genre in form.getlist('genres'):
                    query = 'INSERT INTO film_genres (film_id, genre_id) VALUES (%s, %s);'
                    cursor = mysql.connection.cursor(named_tuple=True)
                    cursor.execute(query, (film, genre))
                    mysql.connection.commit()
                    cursor.close()

    # TODO: Don't forget about genres manytomany fix
    return render_template('films/new.html', context=context)


@app.route('/films/<int:film_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_film(film_id):
    session = Session(engine)
    film = session.query(Films).get(film_id)
    genres_origin = [g.id for g in film.genres_collection]
    print([g.id for g in film.genres_collection])
    context = {
        'genres': session.query(Genres).all(),
        'film': film
    }
    if request.method == 'POST':
        form = request.form
        print(form.getlist('genres'))
        film.name = form['name']
        film.year = form['year']
        film.country = form['country']
        film.description = form['description']
        film.director = form['director']
        film.screenwriter = form['screenwriter']
        film.actors = form['actors']
        film.length = form['length']
        # Genres check and update

        film.genres = [int(i) for i in form.getlist('genres')]
        try:
            session.commit()
        except:
            flash('Ошибка сохранения фильма.', 'danger')
        remove_old = 'DELETE FROM film_genres WHERE film_id = %s;'
        cursor = mysql.connection.cursor(named_tuple=True)
        cursor.execute(remove_old, (film_id, ))
        mysql.connection.commit()
        cursor.close()

        for genre in form.getlist('genres'):
            query = 'INSERT INTO film_genres (film_id, genre_id) VALUES (%s, %s);'
            cursor = mysql.connection.cursor(named_tuple=True)
            cursor.execute(query, (film_id, int(genre)))
            mysql.connection.commit()

        flash('Изменения успешно применены!', 'success')
        return redirect(url_for('view_film', film_id=film_id))

    return render_template('films/new.html', context=context)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') == 'on'
        if login and password:
            cursor = mysql.connection.cursor(named_tuple=True)
            cursor.execute('SELECT * FROM users WHERE login = %s AND password_hash = SHA2(%s, 256);', (login, password))
            db_user = cursor.fetchone()
            cursor.close()
            if db_user:
                    user = User(user_id=db_user.id, login=db_user.login)
                    login_user(user, remember=remember_me)

                    flash('Вы успешно аутентифицированы.', 'success')

                    next = request.args.get('next')

                    return redirect(next or url_for('films'))
        flash('Неверный логин или пароль.', 'danger') 
    return render_template('login.html')    


@app.route('/logout')
def logout():
    logout_user()
    return render_template('index.html')


@app.route('/users')
@login_required
def users():
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT users.*, roles.name AS role_name FROM users LEFT OUTER JOIN roles ON users.role_id = roles.id;')
    users = cursor.fetchall()
    cursor.close()
    return render_template('users/index.html', users=users)


@app.route('/users/new')
@login_required
def new():
    return render_template('users/new.html', user={}, roles=load_roles())


@app.route('/users/<int:user_id>')
@login_required
def show(user_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM users WHERE id = %s;', (user_id,))
    user = cursor.fetchone()
    cursor.execute('SELECT * FROM roles WHERE id = %s;', (user.role_id,))
    role = cursor.fetchone()
    cursor.close()
    return render_template('users/show.html', user=user, role=role)    


@app.route('/users/<int:user_id>/edit')
@login_required
def edit(user_id):
    cursor = mysql.connection.cursor(named_tuple=True)
    cursor.execute('SELECT * FROM users WHERE id = %s;', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return render_template('users/edit.html', user=user, roles=load_roles())


@app.route('/users/create', methods=['POST'])
@login_required
def create():
    login = request.form.get('login') or None
    password = request.form.get('password') or None
    last_name = request.form.get('last_name') or None
    first_name = request.form.get('first_name') or None
    middle_name = request.form.get('middle_name') or None
    role_id = request.form.get('role_id') or None

    query = '''
           INSERT INTO users (login, password_hash, first_name, last_name, middle_name, role_id)
           VALUES (%s, SHA2(%s, 256), %s, %s, %s, %s);
    '''
    cursor = mysql.connection.cursor(named_tuple=True)
    try:
        cursor.execute(query, (login, password, first_name, last_name, middle_name, role_id))
    except connector.errors.DatabaseError:
        flash('Введены некорректные данные. Ошибка сохранения.', 'danger')
        user = {
            'login' : login,
            'password' : password,
            'last_name' : last_name,
            'first_name' : first_name,
            'middle_name' : middle_name,
            'role_id' : role_id
        }
        return render_template('users/new.html', user=user, roles=load_roles())
    mysql.connection.commit()
    cursor.close()
    flash(f'Пользователь {login} был успешно создан.', 'success') 
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update(user_id):
    login = request.form.get('login') or None
    last_name = request.form.get('last_name') or None
    first_name = request.form.get('first_name') or None
    middle_name = request.form.get('middle_name') or None
    role_id = request.form.get('role_id') or None

    query = '''
           UPDATE users SET login=%s, first_name=%s, last_name=%s, 
                            middle_name=%s, role_id=%s
           WHERE id=%s;
    '''
    cursor = mysql.connection.cursor(named_tuple=True)
    try:
        cursor.execute(query, (login, first_name, last_name, middle_name, role_id, user_id))
    except connector.errors.DatabaseError:
        flash('Введены некорректные данные. Ошибка сохранения.', 'danger')
        user = {
            'id' : user_id,
            'login' : login,
            'last_name' : last_name,
            'first_name' : first_name,
            'middle_name' : middle_name,
            'role_id' : role_id
        }
        return render_template('users/edit.html', user=user, roles=load_roles())
    mysql.connection.commit()
    cursor.close()
    flash(f'Данные пользователя {login} были успешно обновлены.', 'success') 
    return redirect(url_for('users'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete(user_id):
    with mysql.connection.cursor(named_tuple=True) as cursor:
        try:
            cursor.execute('DELETE FROM users WHERE id = %s;', (user_id,))
        except connector.errors.DatabaseError:
            flash('Не удалось удалить запись.', 'danger') 
            return redirect(url_for('users'))
        mysql.connection.commit()
        flash(f'Пользователь был успешно удален.', 'success') 

    return redirect(url_for('users'))

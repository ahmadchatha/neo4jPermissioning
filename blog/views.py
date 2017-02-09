from .models import User
from helpers import get_request, create_request, update_object, get_object, apply_exceptions
from flask import Flask, request, session, redirect, url_for, render_template, flash

app = Flask(__name__)

@app.route('/')
def index():
    print(get_request('The Matrix','lifeadmin'))
    #create_request('keanureeves', {'title':'Planet Earth 2', 'desc':'more nature', 'date':1484239365 , 'Budget':125000}, 'life')
    #update_object('permadmin', {"name": "Request", "sfari_applicant_owner_read":['title','desc']})
    #print(get_request('Top Gun','carriemoss'))
    #print(get_object('permadmin','Request'))
    #apply_exceptions('permadmin', 'sfariadmin', 'Request', {'key': 'title', 'value': 'The Matrix'})
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if len(username) < 1:
            flash('Your username must be at least one character.')
        elif len(password) < 5:
            flash('Your password must be at least 5 characters.')
        elif not User(username).register(password):
            flash('A user with that username already exists.')
        else:
            session['username'] = username
            flash('Logged in.')
            return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not User(username).verify_password(password):
            flash('Invalid login.')
        else:
            session['username'] = username
            flash('Logged in.')
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out.')
    return redirect(url_for('index'))



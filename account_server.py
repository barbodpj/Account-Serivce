import sqlite3
import os
from flask import Flask, request, g
from flask.json import jsonify
from http import HTTPStatus
from werkzeug.security import generate_password_hash

app = Flask(__name__)
DATABASE = 'db.sqlite3'


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		db = g._database = sqlite3.connect(DATABASE)
		db.row_factory = dict_factory
	return db


@app.before_first_request
def setup_db():
	cur = get_db().cursor()

	cur.execute('''CREATE TABLE IF NOT EXISTS users 
									(username VARCHAR(15) NOT NULL PRIMARY KEY,
									hashed_passwd TEXT NOT NULL,
									email VARCHAR(320),
									phone VARCHAR(15),
									isAdmin BOOLEAN NOT NULL)''')
	passwd_hashed = generate_password_hash('1234', method='sha256')
	cur.execute("""INSERT OR IGNORE INTO users VALUES 
						('superadmin', ?, NULL, NULL, TRUE)""", 
						(passwd_hashed,))
	get_db().commit()


@app.route('/create_user', methods=['POST'])
def create_user():
	data = request.json
	cur = get_db().cursor()

	try:
		cur.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?)', (data.get('username'),
															data.get('hashed_passwd'),
															data.get('email'),
															data.get('phone'),
															data.get('isAdmin')))
		get_db().commit()
		return {'message': 'Success'}, HTTPStatus.CREATED	
	
	except sqlite3.IntegrityError as e:
		if 'UNIQUE' in str(e):
			return {'message': 'Error: username already exists'}, HTTPStatus.CONFLICT
		else:
			return {'message': 'Error: missing or bad fields'}, HTTPStatus.BAD_REQUEST


@app.route('/get_user/<username>')
def get_user(username):
	cur = get_db().cursor()
	cur.execute('SELECT * FROM users WHERE username = ?', (username,))
	row = cur.fetchone()

	if row is None:
		return {'message': 'Error: No user found'}, HTTPStatus.NOT_FOUND
	else:	
		return {'message': 'Success', 'user': row}, HTTPStatus.OK


@app.route('/modify_user/<username>', methods=['PUT'])
def modify_user(username):
	data = request.json
	cur = get_db().cursor()
	val_list = []
	try:
		for col in data:
			if col == 'isAdmin':
				val_list.append(f'{col} = {data[col]}')
			else:
				val_list.append(f"{col} = '{data[col]}'")

		command = 'UPDATE users SET ' + ','.join(val for val in val_list) + \
					' WHERE username = ?'
		cur.execute(command, (username,))
		get_db().commit()

		if cur.rowcount == 0:
			return {'message': 'Error: No user found'}, HTTPStatus.NOT_FOUND
		else:
			return {'message': 'Success'}, HTTPStatus.OK

	except sqlite3.IntegrityError:
		return {'message': 'Bad fields'}, HTTPStatus.BAD_REQUEST


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__=='__main__':
	app.run()
from flask import Flask, request, render_template, redirect
import psycopg2
import os

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host='db',
        database='postgres',
        user='postgres',
        password='postgres'
    )
    return conn

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        task = request.form['task']
        cur.execute('INSERT INTO tasks (description) VALUES (%s)', (task,))
        conn.commit()
        return redirect('/')
    cur.execute('SELECT id, description FROM tasks')
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', tasks=tasks)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
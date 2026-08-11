from flask import Flask, request, render_template, redirect, url_for
import psycopg2
import os
from datetime import datetime, timedelta
import time

time.sleep(5)

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
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            cur.execute('DELETE FROM tasks WHERE id = %s', (delete_id,))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))
        else:
            task = request.form['task']
            deadline_str = request.form.get('deadline')
            if deadline_str == '':
                deadline = None
            else:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            notify_minutes_str = request.form.get('notify_minutes')
            if notify_minutes_str == '' or notify_minutes_str is None:
                notify_minutes = 0
            else:
                notify_minutes = int(notify_minutes_str)
            cur.execute(
                'INSERT INTO tasks (description, deadline, notify_minutes) VALUES (%s, %s, %s)',
                (task, deadline, notify_minutes)
            )
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))

    cur.execute('SELECT id, description, deadline, notify_minutes, completed FROM tasks ORDER BY id DESC')
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    now = datetime.now()
    processed_tasks = []
    for task in tasks:
        task_id, description, deadline, notify_minutes, completed = task
        status_class = ''
        if completed:
            status_class = 'completed'
        else:
            if deadline:
                if now > deadline:
                    status_class = 'overdue'
                elif notify_minutes and now > (deadline - timedelta(minutes=notify_minutes)):
                    status_class = 'warning'
        processed_tasks.append((task_id, description, deadline, notify_minutes, completed, status_class))

    return render_template('index.html', tasks=processed_tasks)

@app.route('/edit/<int:task_id>', methods=['GET'])
def edit_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, description, deadline, notify_minutes, completed FROM tasks WHERE id = %s', (task_id,))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if task is None:
        return redirect(url_for('index'))
    return render_template('edit.html', task=task)

@app.route('/edit/<int:task_id>', methods=['POST'])
def update_task(task_id):
    task = request.form['task']
    deadline_str = request.form.get('deadline')
    if deadline_str == '':
        deadline = None
    else:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
    notify_minutes_str = request.form.get('notify_minutes')
    if notify_minutes_str == '' or notify_minutes_str is None:
        notify_minutes = 0
    else:
        notify_minutes = int(notify_minutes_str)
    completed = request.form.get('completed') == 'on'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE tasks SET description = %s, deadline = %s, notify_minutes = %s, completed = %s WHERE id = %s',
        (task, deadline, notify_minutes, completed, task_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/complete/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET completed = TRUE WHERE id = %s', (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
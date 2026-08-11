from flask import Flask, request, render_template, redirect, url_for
import psycopg2
import os
from datetime import datetime, timedelta
import time

# Ждём, пока БД поднимется (для локального запуска)
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
        # Проверяем, если запрос на удаление
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            cur.execute('DELETE FROM tasks WHERE id = %s', (delete_id,))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))
        else:
            # Добавление новой задачи
            task = request.form['task']
            deadline = request.form.get('deadline')
            notify_minutes = request.form.get('notify_minutes', 0)
            if deadline == '':
                deadline = None
            else:
                # Преобразуем строку в datetime
                deadline = datetime.strptime(deadline, '%Y-%m-%dT%H:%M')
            cur.execute(
                'INSERT INTO tasks (description, deadline, notify_minutes) VALUES (%s, %s, %s)',
                (task, deadline, notify_minutes)
            )
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))

    # GET запрос — показываем все задачи
    cur.execute('SELECT id, description, deadline, notify_minutes FROM tasks ORDER BY id DESC')
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    # Подсвечиваем просроченные оповещения
    now = datetime.now()
    highlighted_tasks = []
    for task in tasks:
        task_id, description, deadline, notify_minutes = task
        highlight = False
        if deadline and notify_minutes:
            alert_time = deadline - timedelta(minutes=notify_minutes)
            if now > alert_time:
                highlight = True
        highlighted_tasks.append((task_id, description, deadline, notify_minutes, highlight))

    return render_template('index.html', tasks=highlighted_tasks)

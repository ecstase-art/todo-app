from flask import Flask, request, render_template, redirect, url_for
import psycopg2
import os
from datetime import datetime, timedelta
import time

# Небольшая задержка для локального запуска, чтобы БД успела подняться
time.sleep(5)

app = Flask(__name__)

def get_db_connection():
    """
    Подключение к базе данных.
    Если переменная окружения DATABASE_URL задана — используем её (облако).
    Иначе — подключаемся к локальному контейнеру 'db' (Docker Compose).
    """
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Подключение через URL (Cloud.ru или другой хостинг)
        conn = psycopg2.connect(database_url)
    else:
        # Локальный запуск через Docker Compose
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
        # Обработка удаления задачи
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            cur.execute('DELETE FROM tasks WHERE id = %s', (delete_id,))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index'))

        # Обработка добавления новой задачи
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

    # GET-запрос — показываем список задач
    cur.execute('SELECT id, description, deadline, notify_minutes FROM tasks ORDER BY id DESC')
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    # Подсветка задач, у которых прошло время оповещения
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
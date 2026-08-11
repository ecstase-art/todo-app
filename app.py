from flask import Flask, request, render_template, redirect, url_for, session
import psycopg2
import os
from datetime import datetime, timedelta
import time
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

time.sleep(5)

TIMEZONES = [
    {'name': 'Калининград (MSK-1)', 'offset': 2},
    {'name': 'Москва (MSK)', 'offset': 3},
    {'name': 'Самара (MSK+1)', 'offset': 4},
    {'name': 'Екатеринбург (MSK+2)', 'offset': 5},
    {'name': 'Омск (MSK+3)', 'offset': 6},
    {'name': 'Красноярск (MSK+4)', 'offset': 7},
    {'name': 'Иркутск (MSK+5)', 'offset': 8},
    {'name': 'Якутск (MSK+6)', 'offset': 9},
    {'name': 'Владивосток (MSK+7)', 'offset': 10},
    {'name': 'Магадан (MSK+8)', 'offset': 11},
    {'name': 'Камчатка (MSK+9)', 'offset': 12},
]

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
    tz_offset = session.get('timezone_offset', 3)
    sort_by = request.args.get('sort', 'deadline')
    filter_by = request.args.get('filter', 'all')

    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            cur.execute('DELETE FROM tasks WHERE id = %s', (delete_id,))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('index', sort=sort_by, filter=filter_by))
        else:
            task = request.form['task']
            deadline_str = request.form.get('deadline')
            if deadline_str == '':
                deadline = None
            else:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
                deadline = deadline - timedelta(hours=tz_offset)
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
            return redirect(url_for('index', sort=sort_by, filter=filter_by))

    cur.execute('SELECT id, description, deadline, notify_minutes, completed, completed_at FROM tasks')
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    now_utc = datetime.utcnow()

    # === СТАТИСТИКА (по всем задачам, без учёта фильтра) ===
    total_tasks = len(tasks)
    completed_count = 0
    overdue_count = 0
    warning_count = 0
    total_deadline_seconds = 0
    tasks_with_deadline = 0

    for task in tasks:
        _, _, deadline, notify_minutes, completed_flag, _ = task
        if completed_flag:
            completed_count += 1
        else:
            if deadline:
                tasks_with_deadline += 1
                seconds_until = (deadline - now_utc).total_seconds()
                total_deadline_seconds += seconds_until
                if now_utc > deadline:
                    overdue_count += 1
                elif notify_minutes and now_utc > (deadline - timedelta(minutes=notify_minutes)):
                    warning_count += 1

    avg_deadline_seconds = total_deadline_seconds / tasks_with_deadline if tasks_with_deadline > 0 else 0
    # Формируем читаемое среднее время
    if avg_deadline_seconds > 0:
        if avg_deadline_seconds >= 86400:
            days = int(avg_deadline_seconds // 86400)
            hours = int((avg_deadline_seconds % 86400) // 3600)
            avg_deadline_str = f"{days} дн. {hours} ч."
        elif avg_deadline_seconds >= 3600:
            hours = int(avg_deadline_seconds // 3600)
            minutes = int((avg_deadline_seconds % 3600) // 60)
            avg_deadline_str = f"{hours} ч. {minutes} мин."
        else:
            avg_deadline_str = f"{int(avg_deadline_seconds // 60)} мин."
    else:
        avg_deadline_str = "нет данных"

    stats = {
        'total': total_tasks,
        'completed': completed_count,
        'overdue': overdue_count,
        'warning': warning_count,
        'avg_deadline': avg_deadline_str,
    }

    # Фильтрация
    filtered_tasks = []
    for task in tasks:
        task_id, description, deadline, notify_minutes, completed_flag, completed_at = task
        include = True
        if filter_by == 'overdue':
            if completed_flag or deadline is None or now_utc <= deadline:
                include = False
        elif filter_by == 'completed':
            if not completed_flag:
                include = False
        elif filter_by == 'warning':
            if completed_flag or deadline is None or notify_minutes is None or notify_minutes == 0:
                include = False
            else:
                alert_time = deadline - timedelta(minutes=notify_minutes)
                if now_utc <= alert_time:
                    include = False
        if include:
            filtered_tasks.append(task)

    # Сортировка
    if sort_by == 'deadline':
        filtered_tasks.sort(key=lambda x: (x[2] is None, x[2] if x[2] else datetime.max))
    elif sort_by == 'newest':
        filtered_tasks.sort(key=lambda x: x[0], reverse=True)
    elif sort_by == 'completed':
        filtered_tasks.sort(key=lambda x: (x[4], x[2] if x[2] else datetime.max))
    else:
        filtered_tasks.sort(key=lambda x: (x[2] is None, x[2] if x[2] else datetime.max))

    # Подготовка для отображения
    processed_tasks = []
    for task in filtered_tasks:
        task_id, description, deadline, notify_minutes, completed_flag, completed_at = task
        status_class = ''
        if completed_flag:
            status_class = 'completed'
            if completed_at:
                completed_at = completed_at + timedelta(hours=tz_offset)
        else:
            if deadline:
                if now_utc > deadline:
                    status_class = 'overdue'
                elif notify_minutes and now_utc > (deadline - timedelta(minutes=notify_minutes)):
                    status_class = 'warning'
        display_deadline = None
        if deadline:
            display_deadline = deadline + timedelta(hours=tz_offset)
        processed_tasks.append((task_id, description, display_deadline, notify_minutes, completed_flag, completed_at, status_class))

    return render_template('index.html', tasks=processed_tasks,
                           timezones=TIMEZONES, current_tz=tz_offset,
                           sort_by=sort_by, filter_by=filter_by,
                           stats=stats)

@app.route('/edit/<int:task_id>', methods=['GET'])
def edit_task(task_id):
    tz_offset = session.get('timezone_offset', 3)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, description, deadline, notify_minutes, completed, completed_at FROM tasks WHERE id = %s', (task_id,))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if task is None:
        return redirect(url_for('index'))
    task_list = list(task)
    if task_list[2]:
        task_list[2] = task_list[2] + timedelta(hours=tz_offset)
    return render_template('edit.html', task=task_list, timezones=TIMEZONES, current_tz=tz_offset)

@app.route('/edit/<int:task_id>', methods=['POST'])
def update_task(task_id):
    tz_offset = session.get('timezone_offset', 3)
    task = request.form['task']
    deadline_str = request.form.get('deadline')
    if deadline_str == '':
        deadline = None
    else:
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        deadline = deadline - timedelta(hours=tz_offset)
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
    cur.execute('UPDATE tasks SET completed = TRUE, completed_at = NOW() WHERE id = %s', (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    sort = request.args.get('sort', 'deadline')
    filter_by = request.args.get('filter', 'all')
    return redirect(url_for('index', sort=sort, filter=filter_by))

@app.route('/set_timezone', methods=['POST'])
def set_timezone():
    try:
        tz_offset = int(request.form['timezone'])
        session['timezone_offset'] = tz_offset
    except:
        pass
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
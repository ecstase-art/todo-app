from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge
import psycopg2
from datetime import datetime, timedelta
import time
import secrets
import bcrypt
import logging
import requests
import json
import os

# ========================
# Настройка приложения
# ========================
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ========================
# Prometheus метрики
# ========================
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Todo App', version='1.0')

# Кастомные метрики для задач
task_gauge = Gauge('todo_tasks_total', 'Total number of tasks', ['status'])

# ========================
# Логирование в Elasticsearch
# ========================
class ElasticsearchLogger:
    def __init__(self, host='elasticsearch', port=9200):
        self.host = host
        self.port = port
        self.index_prefix = 'app-logs'
        self.url = f'http://{host}:{port}/'

    def log(self, level, message, extra=None):
        doc = {
            '@timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'extra': extra or {}
        }
        index = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
        try:
            requests.post(
                self.url + f'{index}/_doc',
                json=doc,
                timeout=1
            )
        except Exception:
            pass  # не ломаем приложение при проблемах с ES

es_logger = ElasticsearchLogger(
    host=os.environ.get('ES_HOST', 'elasticsearch'),
    port=int(os.environ.get('ES_PORT', 9200))
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_info(message, extra=None):
    logger.info(message)
    es_logger.log('INFO', message, extra)

def log_error(message, extra=None):
    logger.error(message)
    es_logger.log('ERROR', message, extra)

# ========================
# Flask-Login
# ========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа.'

time.sleep(5)  # ожидание БД

# ========================
# Часовые пояса
# ========================
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

# ========================
# Модель пользователя
# ========================
class User(UserMixin):
    def __init__(self, id, username, password_hash, full_name):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.full_name = full_name

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username, password_hash, full_name FROM users WHERE id = %s', (user_id,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

# ========================
# Маршруты: регистрация, вход, выход
# ========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        full_name = request.form['full_name'].strip()
        if not username or not password or not full_name:
            flash('Заполните все поля', 'danger')
            return render_template('register.html')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cur.fetchone():
            flash('Пользователь уже существует', 'danger')
            cur.close()
            conn.close()
            return render_template('register.html')
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute(
            'INSERT INTO users (username, password_hash, full_name) VALUES (%s, %s, %s) RETURNING id',
            (username, password_hash, full_name)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        log_info(f"Новый пользователь зарегистрирован: {username}", {'user_id': user_id, 'full_name': full_name})
        flash('Регистрация успешна! Войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, username, password_hash, full_name FROM users WHERE username = %s', (username,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
            user = User(user_data[0], user_data[1], user_data[2], user_data[3])
            login_user(user)
            log_info(f"Пользователь вошёл: {username}", {'user_id': user.id})
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            log_error(f"Неудачная попытка входа: {username}", {'username': username})
            flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    user = current_user
    logout_user()
    log_info(f"Пользователь вышел: {user.username}", {'user_id': user.id})
    flash('Вы вышли', 'info')
    return redirect(url_for('login'))

# ========================
# Главная страница (список задач)
# ========================
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    tz_offset = session.get('timezone_offset', 3)
    sort_by = request.args.get('sort', 'deadline')
    filter_by = request.args.get('filter', 'all')
    user_id = current_user.id

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        if 'delete_id' in request.form:
            delete_id = request.form['delete_id']
            cur.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', (delete_id, user_id))
            conn.commit()
            cur.close()
            conn.close()
            log_info(f"Удалена задача {delete_id} пользователем {current_user.username}", {'task_id': delete_id, 'user_id': user_id})
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
                'INSERT INTO tasks (user_id, description, deadline, notify_minutes) VALUES (%s, %s, %s, %s)',
                (user_id, task, deadline, notify_minutes)
            )
            conn.commit()
            cur.close()
            conn.close()
            log_info(f"Добавлена задача: {task[:30]}... пользователем {current_user.username}", {'task': task, 'user_id': user_id})
            return redirect(url_for('index', sort=sort_by, filter=filter_by))

    # Получение задач пользователя
    cur.execute('SELECT id, description, deadline, notify_minutes, completed, completed_at FROM tasks WHERE user_id = %s', (user_id,))
    tasks = cur.fetchall()
    cur.close()
    conn.close()

    now_utc = datetime.utcnow()

    # === Статистика ===
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

    # Обновление метрик Prometheus
    task_gauge.labels('total').set(total_tasks)
    task_gauge.labels('completed').set(completed_count)
    task_gauge.labels('overdue').set(overdue_count)
    task_gauge.labels('warning').set(warning_count)

    # === Фильтрация ===
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

    # === Сортировка ===
    if sort_by == 'deadline':
        filtered_tasks.sort(key=lambda x: (x[2] is None, x[2] if x[2] else datetime.max))
    elif sort_by == 'newest':
        filtered_tasks.sort(key=lambda x: x[0], reverse=True)
    elif sort_by == 'completed':
        filtered_tasks.sort(key=lambda x: (x[4], x[2] if x[2] else datetime.max))
    else:
        filtered_tasks.sort(key=lambda x: (x[2] is None, x[2] if x[2] else datetime.max))

    # === Подготовка данных для отображения ===
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
                           stats=stats, user=current_user)

# ========================
# Редактирование задачи
# ========================
@app.route('/edit/<int:task_id>', methods=['GET'])
@login_required
def edit_task(task_id):
    tz_offset = session.get('timezone_offset', 3)
    user_id = current_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, description, deadline, notify_minutes, completed, completed_at FROM tasks WHERE id = %s AND user_id = %s', (task_id, user_id))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if task is None:
        flash('Задача не найдена или доступ запрещён', 'danger')
        return redirect(url_for('index'))
    task_list = list(task)
    if task_list[2]:
        task_list[2] = task_list[2] + timedelta(hours=tz_offset)
    return render_template('edit.html', task=task_list, timezones=TIMEZONES, current_tz=tz_offset)

@app.route('/edit/<int:task_id>', methods=['POST'])
@login_required
def update_task(task_id):
    tz_offset = session.get('timezone_offset', 3)
    user_id = current_user.id
    task_text = request.form['task']
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
        'UPDATE tasks SET description = %s, deadline = %s, notify_minutes = %s, completed = %s WHERE id = %s AND user_id = %s',
        (task_text, deadline, notify_minutes, completed, task_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    log_info(f"Обновлена задача {task_id} пользователем {current_user.username}", {'task_id': task_id, 'user_id': user_id})
    return redirect(url_for('index'))

# ========================
# Отметка задачи выполненной
# ========================
@app.route('/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    user_id = current_user.id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE tasks SET completed = TRUE, completed_at = NOW() WHERE id = %s AND user_id = %s', (task_id, user_id))
    conn.commit()
    cur.close()
    conn.close()
    log_info(f"Задача {task_id} отмечена выполненной пользователем {current_user.username}", {'task_id': task_id, 'user_id': user_id})
    sort = request.args.get('sort', 'deadline')
    filter_by = request.args.get('filter', 'all')
    return redirect(url_for('index', sort=sort, filter=filter_by))

# ========================
# Установка часового пояса
# ========================
@app.route('/set_timezone', methods=['POST'])
@login_required
def set_timezone():
    try:
        tz_offset = int(request.form['timezone'])
        session['timezone_offset'] = tz_offset
        log_info(f"Пользователь {current_user.username} сменил часовой пояс на {tz_offset}", {'user_id': current_user.id, 'tz_offset': tz_offset})
    except:
        pass
    return redirect(url_for('index'))

# ========================
# Запуск приложения
# ========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
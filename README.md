[![Build and Push Docker Image](https://github.com/ecstase-art/todo-app/actions/workflows/docker-build.yml/badge.svg)](https://github.com/ecstase-art/todo-app/actions/workflows/docker-build.yml)

# 📋 Todo App — список задач

Простое приложение для ведения списка задач.  
Работает в контейнерах Docker — **ничего не нужно устанавливать**, кроме Docker.

---

## 🚀 Как запустить (за 2 минуты)

### 1. Установи Docker Desktop
Если у тебя его нет — скачай с [docker.com](https://www.docker.com/products/docker-desktop/) и установи.

### 2. Скачай папку `run-todo`
Скачай весь репозиторий или только папку `run-todo`:

👉 [Скачать run-todo.zip](https://github.com/ecstase-art/todo-app/archive/refs/heads/main.zip)  
(распакуй архив и найди папку `run-todo`)

### 3. Запусти приложение

Выбери свой компьютер:

| Ваша система | Что делать |
|--------------|------------|
| <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/windows11.svg" width="18"> **Windows** | Дважды кликни по файлу **`start-todo.cmd`** |
| <img src="https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/linux.svg" width="18"> **Linux / macOS** | Открой терминал в папке `run-todo` и выполни: `chmod +x start-todo.sh && ./start-todo.sh` |

Через 5–10 секунд откроется браузер с приложением:  
👉 **http://localhost:5000**

---

## 🐳 Локальный запуск через Docker (сборка из исходников)

Если ты скачал **весь репозиторий** (не только папку `run-todo`) и хочешь собрать образ сам — сделай так:

1. Открой терминал в **корневой папке проекта** (там, где лежат `app.py`, `Dockerfile`, `docker-compose.yml`).

2. Выполни команду:
   ```bash
   docker-compose up --build -d

3. Подожди, пока соберётся образ и запустятся контейнеры (это займёт 1–2 минуты).

4. Открой браузер: http://localhost:5000

Отличие от run-todo:

run-todo использует готовый образ с Docker Hub (скачивается быстро).

Локальная сборка использует твой код — удобно, если ты что-то меняешь в приложении.

🛑 Как остановить
В папке run-todo дважды кликни по файлу stop-todo.cmd (Windows) или выполни docker-compose down в терминале (Linux).  

📁 Структура папки run-todo
run-todo/
├── start-todo.cmd          # для Windows
├── start-todo.sh           # для Linux / macOS
├── stop-todo.cmd           # для Windows (остановка)
├── stop-todo.sh            # для Linux / macOS (остановка)
├── docker-compose.yml      # запуск контейнеров
└── init.sql                # создание таблицы в БД
❓ Частые вопросы
Вопрос: При запуске пишет port 5000 already in use
Ответ: Закрой другие программы, которые используют порт 5000, или измени порт в файле docker-compose.yml (вместо "5000:5000" напиши "5001:5000" и открывай http://localhost:5001).

Вопрос: Приложение не открывается в браузере
Ответ: Проверь, что Docker Desktop запущен (значок кита в системном трее). Подожди ещё 10–15 секунд и обнови страницу.

Вопрос: Ошибка could not translate host name "db"
Ответ: Ты запускаешь только контейнер web без базы данных. Используй docker-compose up — он поднимет оба сервиса.

👨‍💻 Автор
ecstase-art

Если что-то не работает — создай Issue в репозитории, я помогу.

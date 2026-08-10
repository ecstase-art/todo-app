#!/bin/bash
echo "Запускаем Todo App..."
docker-compose up -d
echo "Ждём 5 секунд, пока база данных поднимется..."
sleep 5
echo "Открываем браузер..."
xdg-open http://localhost:5000 2>/dev/null || open http://localhost:5000 2>/dev/null || echo "Открой вручную: http://localhost:5000"
echo "Готово! Приложение работает."
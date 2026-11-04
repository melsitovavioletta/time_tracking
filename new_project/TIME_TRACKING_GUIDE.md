# Модуль учёта времени — руководство пользователя

Модуль `time_tracking.py` добавляет в систему управления задачами учёт времени:
сколько времени потрачено на каждую задачу и каждым исполнителем.

## Возможности

| Возможность | Как вызвать |
|---|---|
| Запустить таймер по задаче | `tracker.start_timer(task_id)` |
| Остановить таймер | `tracker.stop_timer(task_id)` |
| Проверить, идёт ли таймер | `tracker.is_running(task_id)` |
| Остановить все таймеры | `tracker.stop_all()` |
| Общее время по задаче | `tracker.get_total_time(task_id)` |
| Общее время пользователя | `tracker.get_user_time(user_id)` |
| Отчёт (словарь / JSON) | `tracker.generate_report()` или `generate_report(user_id=...)` |
| Отчёт в виде таблицы | `tracker.print_report()` |
| Красиво показать время | `format_duration(timedelta)` → `"1 ч 05 мин 30 с"` |

## Быстрый старт

```python
from datetime import datetime, timedelta
from system_design import Priority
from task_manager import TaskManager
from time_tracking import TimeTracker, format_duration

manager = TaskManager()
user = manager.create_user("Алексей", "alexey@company.com")
task = manager.create_task("Разработать API", "Описание",
                           Priority.HIGH, datetime.now() + timedelta(days=7))
manager.assign_task(task.task_id, user.user_id)

tracker = TimeTracker(manager)      # подключаем учёт времени к менеджеру задач

tracker.start_timer(task.task_id)   # начали работать
# ... работа ...
tracker.stop_timer(task.task_id)    # закончили

print(format_duration(tracker.get_total_time(task.task_id)))
tracker.print_report()
```

Пример работы модуля можно посмотреть так:

    python time_tracking.py

## Как это работает

- **Сессия.** Каждый запуск и остановка таймера — это одна сессия (`TimeEntry`).
  По одной задаче может быть сколько угодно сессий, их время складывается.
- **Идущий таймер** тоже учитывается: если таймер не остановлен, в общее время
  входит время с момента запуска до текущего момента. В отчёте такие задачи
  помечены «(идёт)».
- **Несколько задач одновременно.** Таймеры по разным задачам независимы,
  их можно запускать параллельно.
- **Связь с задачами.** Модуль работает с задачами и пользователями из `TaskManager`.
  Если запустить таймер по задаче со статусом «To Do», она автоматически
  переходит в «In Progress». Другие статусы не меняются.

## Отчёт

`generate_report()` возвращает словарь:

```json
{
  "report_generated_at": "2026-01-01T11:35:00",
  "user_id": null,
  "tasks": [
    {
      "task_id": 1,
      "title": "Разработать REST API",
      "assignee": "Алексей Кодлов",
      "status": "In Progress",
      "sessions": 2,
      "seconds": 6600,
      "time": "1 ч 50 мин 00 с",
      "timer_running": true
    }
  ],
  "total_seconds": 6600,
  "total_time": "1 ч 50 мин 00 с"
}
```

Задачи в отчёте отсортированы по времени: сверху те, на которые ушло больше всего.
Чтобы получить отчёт только по одному сотруднику, передайте его id:
`tracker.generate_report(user_id=user.user_id)`.

## Ошибки

При неверных действиях модуль выбрасывает `TimeTrackingError` с понятным сообщением:

| Ситуация | Сообщение |
|---|---|
| Задачи с таким id нет | «Задача с id=… не найдена» |
| Таймер уже запущен | «Таймер для задачи '…' уже запущен» |
| Остановка не запущенного таймера | «Таймер для задачи '…' не запущен» |
| Задача уже выполнена (Done) | «Задача '…' уже выполнена» |

```python
from time_tracking import TimeTrackingError

try:
    tracker.stop_timer(task.task_id)
except TimeTrackingError as e:
    print("Ошибка:", e)
```

## Тесты

    python -m unittest test_time_tracking -v

11 тестов проверяют запуск и остановку таймера, ошибки, подсчёт времени
(в том числе по нескольким сессиям и с идущим таймером), смену статуса задачи и отчёты.
Чтобы тесты не ждали по-настоящему, после запуска таймера они сдвигают время
начала сессии назад (например, «работа началась 30 минут назад»), поэтому проходят мгновенно.

## Ограничения

Данные хранятся только в памяти программы: после её закрытия учёт времени
не сохраняется, как и сами задачи в `TaskManager`.

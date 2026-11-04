from datetime import datetime, timedelta
from typing import List, Dict, Optional

def start(name_func, fail):
    print()
    print("========", name_func, "========")
    try:
        kod = open(fail, encoding="utf-8").read()
        exec(kod, globals())
    except Exception as e:
        print("Ошибка:", e)

start("Анализ требований", "requirements_analysis.py")
start("Проектирование", "system_design.py")
start("Менеджер задач", "task_manager.py")
start("Канбан-доска", "agile_kanban.py")

# пример канбан-доски
manager = TaskManager()
task1 = manager.create_task("Задача 1", "Описание", Priority.MEDIUM, datetime.now())
task2 = manager.create_task("Задача 2", "Описание", Priority.LOW, datetime.now())
board = KanbanBoard([task1, task2], [], [], [])
board.move_task(task1, "todo", "done")
print("Статистика доски:", board.get_board_stats())

start("Тесты", "test_task_system.py")
start("Мониторинг", "maintenance_monitoring.py")
start("Развертывание", "deployment_script.py")
start("Учёт времени", "time_tracking.py")
start("Тесты учёта времени", "test_time_tracking.py")

print()
print("Готово!")

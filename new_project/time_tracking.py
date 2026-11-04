import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from system_design import Priority, Status, Task
from task_manager import TaskManager


class TimeTrackingError(Exception):
    """Ошибка учёта времени (неверная задача, таймер уже запущен и т.п.)."""


@dataclass
class TimeEntry:
    """Один отрезок работы над задачей: от старта до остановки таймера."""
    task_id: int
    start: datetime
    end: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        return self.end is None

    def duration(self, now: Optional[datetime] = None) -> timedelta:
        """Длительность отрезка. Для идущего таймера считается до момента now."""
        finish = self.end if self.end is not None else (now or datetime.now())
        return finish - self.start


def format_duration(duration: timedelta) -> str:
    """Переводит время в удобный вид, например '1 ч 05 мин 30 с'."""
    total_seconds = int(duration.total_seconds())
    hours, rest = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours} ч {minutes:02d} мин {seconds:02d} с"


class TimeTracker:
    """Учёт времени по задачам из TaskManager."""

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.entries: List[TimeEntry] = []
        self.active: Dict[int, TimeEntry] = {}  # task_id -> идущий отрезок

    # ---------- таймер ----------

    def _get_task(self, task_id: int) -> Task:
        task = self.task_manager.tasks.get(task_id)
        if task is None:
            raise TimeTrackingError(f"Задача с id={task_id} не найдена")
        return task

    def start_timer(self, task_id: int) -> TimeEntry:
        """Запускает таймер для задачи."""
        task = self._get_task(task_id)
        if task_id in self.active:
            raise TimeTrackingError(f"Таймер для задачи '{task.title}' уже запущен")
        if task.status == Status.DONE:
            raise TimeTrackingError(f"Задача '{task.title}' уже выполнена")

        entry = TimeEntry(task_id=task_id, start=datetime.now())
        self.active[task_id] = entry
        self.entries.append(entry)

        # Интеграция: если по задаче началась работа, она переходит "в работу"
        if task.status == Status.TODO:
            task.update_status(Status.IN_PROGRESS)
        return entry

    def stop_timer(self, task_id: int) -> TimeEntry:
        """Останавливает таймер и возвращает завершённый отрезок."""
        task = self._get_task(task_id)
        entry = self.active.pop(task_id, None)
        if entry is None:
            raise TimeTrackingError(f"Таймер для задачи '{task.title}' не запущен")
        entry.end = datetime.now()
        return entry

    def is_running(self, task_id: int) -> bool:
        return task_id in self.active

    def stop_all(self) -> List[TimeEntry]:
        """Останавливает все запущенные таймеры (например, в конце рабочего дня)."""
        return [self.stop_timer(task_id) for task_id in list(self.active)]

    # ---------- подсчёт времени ----------

    def get_task_entries(self, task_id: int) -> List[TimeEntry]:
        return [e for e in self.entries if e.task_id == task_id]

    def get_total_time(self, task_id: int) -> timedelta:
        """Общее время по задаче, включая идущий сейчас таймер."""
        self._get_task(task_id)
        now = datetime.now()
        return sum((e.duration(now) for e in self.get_task_entries(task_id)), timedelta())

    def get_user_time(self, user_id: int) -> timedelta:
        """Общее время по всем задачам, назначенным пользователю."""
        tasks = self.task_manager.get_user_tasks(user_id)
        return sum((self.get_total_time(t.task_id) for t in tasks), timedelta())

    # ---------- отчёты ----------

    def generate_report(self, user_id: Optional[int] = None) -> Dict:
        """
        Отчёт по времени. Без user_id - по всем задачам,
        с user_id - только по задачам этого пользователя.
        """
        if user_id is None:
            tasks = list(self.task_manager.tasks.values())
        else:
            tasks = self.task_manager.get_user_tasks(user_id)

        rows = []
        total = timedelta()
        for task in tasks:
            spent = self.get_total_time(task.task_id)
            total += spent
            rows.append({
                "task_id": task.task_id,
                "title": task.title,
                "assignee": task.assignee.name if task.assignee else None,
                "status": task.status.value,
                "sessions": len(self.get_task_entries(task.task_id)),
                "seconds": int(spent.total_seconds()),
                "time": format_duration(spent),
                "timer_running": self.is_running(task.task_id),
            })

        # Сначала задачи, на которые ушло больше всего времени
        rows.sort(key=lambda row: row["seconds"], reverse=True)

        return {
            "report_generated_at": datetime.now().isoformat(),
            "user_id": user_id,
            "tasks": rows,
            "total_seconds": int(total.total_seconds()),
            "total_time": format_duration(total),
        }

    def print_report(self, user_id: Optional[int] = None) -> None:
        """Печатает отчёт в виде простой таблицы."""
        report = self.generate_report(user_id)
        print(f"{'Задача':<30} {'Исполнитель':<18} {'Сессий':>6}  Время")
        print("-" * 75)
        for row in report["tasks"]:
            mark = " (идёт)" if row["timer_running"] else ""
            print(f"{row['title'][:30]:<30} {(row['assignee'] or '-')[:18]:<18} "
                  f"{row['sessions']:>6}  {row['time']}{mark}")
        print("-" * 75)
        print(f"{'Итого:':<56} {report['total_time']}")


# Демонстрация работы модуля
def demo_time_tracking():
    manager = TaskManager()
    dev = manager.create_user("Алексей Кодлов", "alexey@company.com")
    api = manager.create_task("Разработать REST API", "API для задач",
                              Priority.HIGH, datetime.now() + timedelta(days=7))
    docs = manager.create_task("Написать документацию", "Руководство",
                               Priority.LOW, datetime.now() + timedelta(days=7))
    manager.assign_task(api.task_id, dev.user_id)
    manager.assign_task(docs.task_id, dev.user_id)

    tracker = TimeTracker(manager)

    # Работаем по-настоящему, но всего несколько секунд
    print("Работаем над API 3 секунды...")
    tracker.start_timer(api.task_id)
    time.sleep(3)
    tracker.stop_timer(api.task_id)

    print("Работаем над документацией 2 секунды...")
    tracker.start_timer(docs.task_id)
    time.sleep(2)
    tracker.stop_timer(docs.task_id)

    print("Снова берёмся за API, таймер пока не останавливаем...")
    tracker.start_timer(api.task_id)
    time.sleep(1)  # таймер ещё идёт
    print()

    tracker.print_report()
    print(f"\nВсего у {dev.name}: {format_duration(tracker.get_user_time(dev.user_id))}")
    print("\nОтчёт в формате JSON:")
    print(json.dumps(tracker.generate_report(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    demo_time_tracking()

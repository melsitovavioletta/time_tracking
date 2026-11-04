import unittest
from datetime import datetime, timedelta

from system_design import Priority, Status
from task_manager import TaskManager
from time_tracking import TimeTracker, TimeTrackingError


def seconds(duration):
    """Время в целых секундах (доли секунды, пока выполняется тест, отбрасываем)."""
    return int(duration.total_seconds())


class TestTimeTracking(unittest.TestCase):
    def setUp(self):
        self.manager = TaskManager()
        self.user = self.manager.create_user("Тест User", "test@test.com")
        due = datetime.now() + timedelta(days=7)
        self.task = self.manager.create_task("Задача A", "Описание", Priority.HIGH, due)
        self.task2 = self.manager.create_task("Задача B", "Описание", Priority.LOW, due)
        self.tracker = TimeTracker(self.manager)

    def start_minutes_ago(self, task, minutes):
        """Запускает таймер и сдвигает его начало назад,
        как будто работа над задачей началась minutes минут назад.
        Так тесту не нужно ждать по-настоящему."""
        entry = self.tracker.start_timer(task.task_id)
        entry.start -= timedelta(minutes=minutes)
        return entry

    # --- старт / стоп ---

    def test_start_and_stop_timer(self):
        self.start_minutes_ago(self.task, 30)
        self.assertTrue(self.tracker.is_running(self.task.task_id))
        entry = self.tracker.stop_timer(self.task.task_id)
        self.assertFalse(self.tracker.is_running(self.task.task_id))
        self.assertEqual(seconds(entry.duration()), 30 * 60)

    def test_start_twice_raises(self):
        self.tracker.start_timer(self.task.task_id)
        with self.assertRaises(TimeTrackingError):
            self.tracker.start_timer(self.task.task_id)

    def test_stop_without_start_raises(self):
        with self.assertRaises(TimeTrackingError):
            self.tracker.stop_timer(self.task.task_id)

    def test_unknown_task_raises(self):
        with self.assertRaises(TimeTrackingError):
            self.tracker.start_timer(999)

    def test_cannot_start_done_task(self):
        self.task.update_status(Status.DONE)
        with self.assertRaises(TimeTrackingError):
            self.tracker.start_timer(self.task.task_id)

    # --- общее время ---

    def test_total_time_sums_sessions(self):
        for minutes in (20, 40):
            self.start_minutes_ago(self.task, minutes)
            self.tracker.stop_timer(self.task.task_id)
        self.assertEqual(seconds(self.tracker.get_total_time(self.task.task_id)), 60 * 60)

    def test_total_time_includes_running_timer(self):
        self.start_minutes_ago(self.task, 15)
        self.assertEqual(seconds(self.tracker.get_total_time(self.task.task_id)), 15 * 60)

    def test_user_time(self):
        self.manager.assign_task(self.task.task_id, self.user.user_id)
        self.manager.assign_task(self.task2.task_id, self.user.user_id)
        self.start_minutes_ago(self.task, 10)
        self.tracker.stop_timer(self.task.task_id)
        self.start_minutes_ago(self.task2, 5)
        self.tracker.stop_timer(self.task2.task_id)
        self.assertEqual(seconds(self.tracker.get_user_time(self.user.user_id)), 15 * 60)

    # --- интеграция с системой задач ---

    def test_start_moves_todo_task_in_progress(self):
        self.assertEqual(self.task.status, Status.TODO)
        self.tracker.start_timer(self.task.task_id)
        self.assertEqual(self.task.status, Status.IN_PROGRESS)

    # --- отчёты ---

    def test_report_all_tasks(self):
        self.manager.assign_task(self.task.task_id, self.user.user_id)
        self.start_minutes_ago(self.task, 65)
        self.tracker.stop_timer(self.task.task_id)
        self.start_minutes_ago(self.task2, 10)  # таймер не останавливаем

        report = self.tracker.generate_report()
        self.assertEqual(report["total_seconds"], 75 * 60)
        self.assertEqual(report["total_time"], "1 ч 15 мин 00 с")
        self.assertEqual(len(report["tasks"]), 2)
        first = report["tasks"][0]  # больше всего времени - первая
        self.assertEqual(first["title"], "Задача A")
        self.assertEqual(first["assignee"], "Тест User")
        self.assertEqual(first["sessions"], 1)
        self.assertFalse(first["timer_running"])
        self.assertTrue(report["tasks"][1]["timer_running"])

    def test_report_for_user(self):
        self.manager.assign_task(self.task.task_id, self.user.user_id)
        self.start_minutes_ago(self.task2, 10)
        self.tracker.stop_timer(self.task2.task_id)

        report = self.tracker.generate_report(user_id=self.user.user_id)
        self.assertEqual(len(report["tasks"]), 1)
        self.assertEqual(report["total_seconds"], 0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTimeTracking)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print(f"\nРезультаты тестирования учёта времени:")
    print(f"Пройдено тестов: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалено тестов: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")

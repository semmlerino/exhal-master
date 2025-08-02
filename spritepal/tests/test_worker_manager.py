"""
Test the WorkerManager utility class.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from ui.common import WorkerManager


class DummyWorker(QThread):
    """Simple test worker that can be controlled"""

    finished_work = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.should_run = True
        self.work_done = False

    def run(self):
        """Simple work simulation"""
        # Simulate some work
        self.msleep(50)  # Sleep for 50ms
        if self.should_run:
            self.work_done = True
            self.finished_work.emit()

    def stop(self):
        """Stop the worker"""
        self.should_run = False
        self.quit()


class TestWorkerManager:
    """Test WorkerManager functionality"""

    def test_cleanup_none_worker(self):
        """Test cleanup handles None worker gracefully"""
        # Should not raise any exception
        WorkerManager.cleanup_worker(None)

    def test_cleanup_stopped_worker(self):
        """Test cleanup of already stopped worker"""
        worker = DummyWorker()
        # Worker is not running, cleanup should handle gracefully
        WorkerManager.cleanup_worker(worker)

    def test_cleanup_running_worker(self, qtbot):
        """Test cleanup of running worker with graceful shutdown"""
        worker = DummyWorker()

        # Start worker
        worker.start()
        qtbot.waitUntil(worker.isRunning, timeout=1000)

        # Clean up should stop it gracefully
        WorkerManager.cleanup_worker(worker, timeout=500)

        # Worker should be stopped
        assert not worker.isRunning()

    def test_cleanup_force_terminate_disabled(self, qtbot):
        """Test cleanup behavior when force_terminate is disabled"""
        class SlowWorker(QThread):
            """Worker that takes time to stop"""
            def __init__(self):
                super().__init__()
                self._should_stop = False

            def run(self):
                # Run until told to stop
                while not self._should_stop:
                    self.msleep(10)

            def quit(self):
                """Override quit to set stop flag"""
                self._should_stop = True
                super().quit()

        worker = SlowWorker()

        # Start worker
        worker.start()
        qtbot.waitUntil(worker.isRunning, timeout=1000)

        # Cleanup without forced termination should respect the timeout
        WorkerManager.cleanup_worker(worker, timeout=500, force_terminate=False)

        # Worker should be stopped since our quit() implementation works
        assert not worker.isRunning()

    def test_cleanup_already_stopping(self, qtbot):
        """Test cleanup of a worker that's already stopping"""
        worker = DummyWorker()

        # Start and immediately quit
        worker.start()
        qtbot.waitUntil(worker.isRunning, timeout=1000)
        worker.quit()

        # Cleanup should handle gracefully
        WorkerManager.cleanup_worker(worker, timeout=500)

        # Worker should be stopped
        assert not worker.isRunning()

    def test_start_worker(self, qtbot):
        """Test starting a worker"""
        worker = DummyWorker()

        # Start worker
        WorkerManager.start_worker(worker)

        # Worker should be running
        qtbot.waitUntil(worker.isRunning, timeout=1000)
        assert worker.isRunning()

        # Cleanup
        worker.stop()
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=1000)

    def test_start_with_cleanup(self, qtbot):
        """Test starting a worker with cleanup of existing one"""
        old_worker = DummyWorker()
        old_worker.start()
        qtbot.waitUntil(old_worker.isRunning, timeout=1000)

        new_worker = DummyWorker()

        # Start new worker, should cleanup old one
        WorkerManager.start_worker(new_worker, cleanup_existing=old_worker)

        # Old worker should be stopped
        qtbot.waitUntil(lambda: not old_worker.isRunning(), timeout=2000)
        assert not old_worker.isRunning()

        # New worker should be running
        assert new_worker.isRunning()

        # Cleanup
        new_worker.stop()
        qtbot.waitUntil(lambda: not new_worker.isRunning(), timeout=1000)

    def test_create_and_start(self, qtbot):
        """Test create_and_start helper"""
        # Create and start in one call
        worker = WorkerManager.create_and_start(DummyWorker)

        # Worker should be running
        qtbot.waitUntil(worker.isRunning, timeout=1000)
        assert worker.isRunning()
        assert isinstance(worker, DummyWorker)

        # Cleanup
        worker.stop()
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=1000)

    def test_create_and_start_with_cleanup(self, qtbot):
        """Test create_and_start with existing worker cleanup"""
        # Create old worker
        old_worker = DummyWorker()
        old_worker.start()
        qtbot.waitUntil(old_worker.isRunning, timeout=1000)

        # Create new worker, cleaning up old one
        new_worker = WorkerManager.create_and_start(
            DummyWorker,
            cleanup_existing=old_worker
        )

        # Old worker should be stopped
        qtbot.waitUntil(lambda: not old_worker.isRunning(), timeout=2000)

        # New worker should be running
        assert new_worker.isRunning()

        # Cleanup
        new_worker.stop()
        qtbot.waitUntil(lambda: not new_worker.isRunning(), timeout=1000)

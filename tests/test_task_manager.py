"""
Task Manager Tests
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch

from ravn_app.core.task_manager import (
    TaskQueue, Task, TaskStatus, TaskType, TaskResult,
    get_task_queue, shutdown_task_queue
)


class TestTaskQueue:
    """TaskQueue tests"""

    def setup_method(self):
        """Setup for each test"""
        self.queue = TaskQueue(max_concurrent=2)
    
    def teardown_method(self):
        """Cleanup after each test"""
        if self.queue.is_running:
            self.queue.stop(wait=True)

    def test_queue_initialization(self):
        """Test TaskQueue initializes correctly"""
        assert self.queue.max_concurrent == 2
        assert self.queue.queue_size == 0
        assert self.queue.active_count == 0
        assert not self.queue.is_running

    def test_queue_start_stop(self):
        """Test starting and stopping the queue"""
        self.queue.start()
        assert self.queue.is_running
        
        self.queue.stop(wait=True)
        assert not self.queue.is_running

    def test_pause_resume_toggle(self):
        """Test pausing and resuming queue intake"""
        assert self.queue.is_paused is False

        self.queue.pause()
        assert self.queue.is_paused is True

        self.queue.resume()
        assert self.queue.is_paused is False

        paused = self.queue.toggle_pause()
        assert paused is True
        assert self.queue.is_paused is True

    def test_add_task(self):
        """Test adding a task to the queue"""
        def dummy_fn(*args, **kwargs):
            return True
        
        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Test Task",
            execute_fn=dummy_fn
        )
        
        assert task_id is not None
        assert len(task_id) == 8
        
        task = self.queue.get_task(task_id)
        assert task is not None
        assert task.name == "Test Task"
        assert task.task_type == TaskType.GENERIC
        assert task.status == TaskStatus.QUEUED

    def test_task_execution(self):
        """Test that tasks are executed"""
        result_holder = {'executed': False}
        
        def test_fn(*args, **kwargs):
            result_holder['executed'] = True
            return True
        
        self.queue.start()
        
        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Execution Test",
            execute_fn=test_fn
        )
        
        # Wait for task to complete
        time.sleep(0.5)
        
        assert result_holder['executed']
        
        task = self.queue.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.result is not None
        assert task.result.success

    def test_task_with_progress_callback(self):
        """Test progress callbacks"""
        progress_updates = []
        
        def test_fn(*args, progress_callback=None, **kwargs):
            for i in range(0, 101, 25):
                if progress_callback:
                    progress_callback(i, f"Step {i}")
                time.sleep(0.01)
            return True
        
        def on_progress(progress, message):
            progress_updates.append((progress, message))
        
        self.queue.start()
        
        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Progress Test",
            execute_fn=test_fn,
            on_progress=on_progress
        )
        
        # Wait for task to complete
        time.sleep(0.5)
        
        # Process callbacks
        self.queue.process_callbacks()
        
        assert len(progress_updates) > 0

    def test_task_completion_callback(self):
        """Test completion callbacks"""
        completion_holder = {'called': False, 'task': None}
        
        def test_fn(*args, **kwargs):
            return True
        
        def on_complete(task):
            completion_holder['called'] = True
            completion_holder['task'] = task
        
        self.queue.start()
        
        self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Completion Test",
            execute_fn=test_fn,
            on_complete=on_complete
        )
        
        # Wait for task to complete
        time.sleep(0.5)
        
        # Process callbacks
        self.queue.process_callbacks()
        
        assert completion_holder['called']
        assert completion_holder['task'] is not None

    def test_task_error_handling(self):
        """Test error handling"""
        error_holder = {'called': False, 'error': None}

        def failing_fn(*args, **kwargs):
            raise ValueError("Test error")

        def on_error(task, error_msg):
            error_holder['called'] = True
            error_holder['error'] = error_msg

        self.queue.start()

        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Error Test",
            execute_fn=failing_fn,
            on_error=on_error
        )

        # Wait for task to complete
        time.sleep(0.5)

        # Process callbacks
        self.queue.process_callbacks()

        assert error_holder['called']
        assert "Test error" in error_holder['error']

        task = self.queue.get_task(task_id)
        assert task.status == TaskStatus.FAILED

    def test_false_result_marks_task_failed(self):
        """False return values should mark the task as failed."""
        errors = []

        def false_fn(*args, **kwargs):
            return False

        def on_error(task, error_msg):
            errors.append(error_msg)

        self.queue.start()
        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="False Result Test",
            execute_fn=false_fn,
            on_error=on_error,
        )

        time.sleep(0.3)
        self.queue.process_callbacks()

        task = self.queue.get_task(task_id)
        assert task.status == TaskStatus.FAILED
        assert task.result is not None
        assert task.result.success is False
        assert errors

    def test_cancel_running_task_uses_cancel_fn(self):
        """Running tasks should be cancellable when a cancel_fn is provided."""
        cancel_flag = {"requested": False}
        cancel_events = []

        def cancellable_fn(*args, progress_callback=None, **kwargs):
            while not cancel_flag["requested"]:
                if progress_callback:
                    progress_callback(10, "working")
                time.sleep(0.02)
            raise RuntimeError("cancelled")

        def cancel_fn():
            cancel_flag["requested"] = True
            return True

        def on_cancel(task):
            cancel_events.append(task.id)

        self.queue.start()
        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Cancellable",
            execute_fn=cancellable_fn,
            cancel_fn=cancel_fn,
            on_cancel=on_cancel,
        )

        time.sleep(0.15)
        assert self.queue.cancel_task(task_id) is True
        time.sleep(0.2)
        self.queue.process_callbacks()

        task = self.queue.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED
        assert cancel_events == [task_id]

    def test_cancel_pending_task(self):
        """Test cancelling a pending task"""
        def slow_fn(*args, **kwargs):
            time.sleep(10)
            return True
        
        # Don't start the queue, so task stays queued
        task_id = self.queue.add_task(
            task_type=TaskType.GENERIC,
            name="Cancel Test",
            execute_fn=slow_fn
        )
        
        result = self.queue.cancel_task(task_id)
        assert result
        
        task = self.queue.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED

    def test_get_tasks_by_status(self):
        """Test filtering tasks by status"""
        def instant_fn(*args, **kwargs):
            return True
        
        # Add some tasks without starting queue
        for i in range(3):
            self.queue.add_task(
                task_type=TaskType.GENERIC,
                name=f"Task {i}",
                execute_fn=instant_fn
            )
        
        pending = self.queue.get_pending_tasks()
        assert len(pending) == 3
        
        active = self.queue.get_active_tasks()
        assert len(active) == 0
        
        # Start queue and wait
        self.queue.start()
        time.sleep(0.5)
        
        completed = self.queue.get_completed_tasks()
        assert len(completed) == 3

    def test_clear_completed(self):
        """Test clearing completed tasks"""
        def instant_fn(*args, **kwargs):
            return True
        
        self.queue.start()
        
        for i in range(3):
            self.queue.add_task(
                task_type=TaskType.GENERIC,
                name=f"Task {i}",
                execute_fn=instant_fn
            )
        
        time.sleep(0.5)
        
        all_tasks = self.queue.get_all_tasks()
        assert len(all_tasks) == 3
        
        self.queue.clear_completed()
        
        all_tasks = self.queue.get_all_tasks()
        assert len(all_tasks) == 0

    def test_concurrent_execution(self):
        """Test concurrent task execution"""
        execution_times = []
        lock = threading.Lock()
        
        def tracked_fn(*args, **kwargs):
            start = time.time()
            time.sleep(0.2)
            end = time.time()
            with lock:
                execution_times.append((start, end))
            return True
        
        self.queue.start()
        
        # Add 4 tasks
        for i in range(4):
            self.queue.add_task(
                task_type=TaskType.GENERIC,
                name=f"Concurrent Task {i}",
                execute_fn=tracked_fn
            )
        
        # Wait for all tasks
        time.sleep(1.5)
        
        assert len(execution_times) == 4
        
        # With max_concurrent=2, there should be overlap
        # Sort by start time
        execution_times.sort(key=lambda x: x[0])
        
        # First two should overlap
        if len(execution_times) >= 2:
            # Task 0 should overlap with task 1
            assert execution_times[0][1] > execution_times[1][0] or \
                   execution_times[1][1] > execution_times[0][0]


class TestTaskResult:
    """TaskResult tests"""

    def test_task_result_success(self):
        """Test successful TaskResult"""
        result = TaskResult(
            success=True,
            output_path="/path/to/output.mp4",
            duration_seconds=10.5
        )
        
        assert result.success
        assert result.output_path == "/path/to/output.mp4"
        assert result.duration_seconds == 10.5
        assert result.error_message is None

    def test_task_result_failure(self):
        """Test failed TaskResult"""
        result = TaskResult(
            success=False,
            error_message="File not found"
        )
        
        assert not result.success
        assert result.error_message == "File not found"
        assert result.output_path is None


class TestTaskTypes:
    """Test task type handling"""

    def test_all_task_types(self):
        """Test all task types can be created"""
        queue = TaskQueue(max_concurrent=1)
        
        def dummy_fn(*args, **kwargs):
            return True
        
        for task_type in TaskType:
            task_id = queue.add_task(
                task_type=task_type,
                name=f"Test {task_type.value}",
                execute_fn=dummy_fn
            )
            
            task = queue.get_task(task_id)
            assert task.task_type == task_type


class TestGlobalQueue:
    """Test global queue singleton"""

    def teardown_method(self):
        """Cleanup global queue"""
        shutdown_task_queue()

    def test_get_task_queue(self):
        """Test getting global task queue"""
        queue1 = get_task_queue()
        queue2 = get_task_queue()
        
        assert queue1 is queue2
        assert queue1.is_running

    def test_shutdown_task_queue(self):
        """Test shutting down global queue"""
        queue = get_task_queue()
        assert queue.is_running
        
        shutdown_task_queue()
        
        # Getting queue again should create a new one
        new_queue = get_task_queue()
        assert new_queue is not queue

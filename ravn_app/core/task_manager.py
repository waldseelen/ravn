"""
RAVN - Task/Queue Manager
Unified queue and task management for long-running operations
"""

import threading
import queue
import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status states"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskType(Enum):
    """Types of tasks supported"""
    DOWNLOAD = "download"
    CONVERT = "convert"
    MERGE = "merge"
    NORMALIZE = "normalize"
    SUBTITLE = "subtitle"
    GENERIC = "generic"
    TORRENT = "torrent"
    MIXER_AUDIO = "mixer_audio"
    MIXER_VIDEO = "mixer_video"
    APPLY_FILTERS = "apply_filters"
    LIBRARY_SCAN = "library_scan"


@dataclass
class TaskResult:
    """Result of a completed task"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Represents a task in the queue"""
    id: str
    task_type: TaskType
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    progress_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None

    # Task execution details
    execute_fn: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    cancel_fn: Optional[Callable[[], bool]] = None
    cancel_requested: bool = False

    # Callbacks
    on_progress: Optional[Callable[[int, str], None]] = None
    on_complete: Optional[Callable[['Task'], None]] = None
    on_error: Optional[Callable[['Task', str], None]] = None
    on_cancel: Optional[Callable[['Task'], None]] = None

    def __hash__(self):
        return hash(self.id)


class TaskQueue:
    """Thread-safe task queue with priority support"""
    
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self._queue: queue.Queue = queue.Queue()
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._workers: List[threading.Thread] = []
        self._running = False
        self._paused = False
        self._active_count = 0
        
        # Thread-safe callbacks (called from main thread or via queue)
        self._callback_queue: queue.Queue = queue.Queue()
        
        logger.info(f"TaskQueue initialized with max_concurrent={max_concurrent}")
    
    def add_task(
        self,
        task_type: TaskType,
        name: str,
        execute_fn: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_complete: Optional[Callable[[Task], None]] = None,
        on_error: Optional[Callable[[Task, str], None]] = None,
        cancel_fn: Optional[Callable[[], bool]] = None,
        on_cancel: Optional[Callable[[Task], None]] = None,
    ) -> str:
        """
        Add a new task to the queue
        
        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())[:8]
        
        task = Task(
            id=task_id,
            task_type=task_type,
            name=name,
            status=TaskStatus.QUEUED,
            execute_fn=execute_fn,
            args=args,
            kwargs=kwargs or {},
            cancel_fn=cancel_fn,
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error,
            on_cancel=on_cancel,
        )
        
        with self._lock:
            self._tasks[task_id] = task
            self._queue.put(task)
        
        logger.info(f"Task added: {task_id} - {name} ({task_type.value})")
        return task_id
    
    def start(self):
        """Start the task queue workers"""
        if self._running:
            return
        
        self._running = True
        
        for i in range(self.max_concurrent):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"TaskQueue started with {self.max_concurrent} workers")
    
    def stop(self, wait: bool = True):
        """Stop the task queue"""
        self._running = False
        
        # Add sentinel values to wake up workers
        for _ in self._workers:
            self._queue.put(None)
        
        if wait:
            for worker in self._workers:
                worker.join(timeout=5.0)
        
        self._workers.clear()
        logger.info("TaskQueue stopped")
    
    def _worker_loop(self):
        """Worker thread main loop"""
        while self._running:
            try:
                while self._paused and self._running:
                    time.sleep(0.05)

                task = self._queue.get(timeout=1.0)

                if task is None:  # Sentinel value
                    break
                if task.status == TaskStatus.CANCELLED:
                    continue

                self._execute_task(task)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    @staticmethod
    def _extract_output_path(task: Task, result: Any = None) -> Optional[str]:
        """Best-effort output path discovery for heterogeneous task result types."""
        candidates = [
            task.kwargs.get('output_path'),
            task.kwargs.get('output_file'),
            getattr(result, 'output_path', None),
            getattr(result, 'output_file', None),
        ]

        output_files = getattr(result, 'output_files', None)
        if isinstance(output_files, (list, tuple)) and output_files:
            candidates.append(output_files[0])

        metadata = getattr(result, 'metadata', None)
        if isinstance(metadata, dict):
            candidates.extend([
                metadata.get('output_path'),
                metadata.get('output_file'),
            ])

        for candidate in candidates:
            if isinstance(candidate, str) and candidate:
                return candidate
        return None

    def _coerce_task_result(self, task: Task, result: Any) -> TaskResult:
        """Normalize arbitrary execution results into TaskResult."""
        if isinstance(result, TaskResult):
            return result

        if isinstance(result, bool):
            return TaskResult(success=result, output_path=self._extract_output_path(task))

        if isinstance(result, tuple) and len(result) >= 2:
            return TaskResult(
                success=bool(result[0]),
                output_path=result[1] if len(result) > 1 else None,
                error_message=result[2] if len(result) > 2 else None,
            )

        if hasattr(result, 'success'):
            raw_metadata = getattr(result, 'metadata', {})
            metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {'raw_result': result}
            return TaskResult(
                success=bool(getattr(result, 'success', False)),
                output_path=self._extract_output_path(task, result),
                error_message=getattr(result, 'error_message', None) or getattr(result, 'stderr', None) or None,
                metadata=metadata,
            )

        return TaskResult(
            success=True,
            output_path=self._extract_output_path(task, result),
            metadata={'raw_result': result},
        )

    def _queue_callback(self, callback_type: str, *payload: Any) -> None:
        self._callback_queue.put((callback_type, *payload))

    def _execute_task(self, task: Task):
        """Execute a single task"""
        with self._lock:
            if task.status == TaskStatus.CANCELLED:
                return
            self._active_count += 1
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

        logger.info(f"Task started: {task.id} - {task.name}")

        try:
            def progress_wrapper(progress: int, message: str = ""):
                if task.cancel_requested:
                    return
                task.progress = progress
                task.progress_message = message
                if task.on_progress:
                    self._queue_callback('progress', task, progress, message)

            raw_result = None
            if task.execute_fn:
                raw_result = task.execute_fn(
                    *task.args,
                    progress_callback=progress_wrapper,
                    **task.kwargs
                )

            task_result = self._coerce_task_result(task, raw_result)

            with self._lock:
                task.completed_at = datetime.now()
                if task.started_at:
                    task_result.duration_seconds = (task.completed_at - task.started_at).total_seconds()
                task.result = task_result

                if task.cancel_requested:
                    task.status = TaskStatus.CANCELLED
                elif task_result.success:
                    task.status = TaskStatus.COMPLETED
                    task.progress = max(task.progress, 100)
                else:
                    task.status = TaskStatus.FAILED

            if task.status == TaskStatus.CANCELLED:
                logger.info(f"Task cancelled during execution: {task.id}")
                if task.on_cancel:
                    self._queue_callback('cancel', task)
            elif task.status == TaskStatus.COMPLETED:
                logger.info(f"Task completed: {task.id} - {task.name}")
                if task.on_complete:
                    self._queue_callback('complete', task)
            else:
                error_msg = task_result.error_message or "Task failed"
                logger.error(f"Task failed: {task.id} - {error_msg}")
                if task.on_error:
                    self._queue_callback('error', task, error_msg)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task failed: {task.id} - {error_msg}")

            with self._lock:
                task.completed_at = datetime.now()
                duration_seconds = 0.0
                if task.started_at and task.completed_at:
                    duration_seconds = (task.completed_at - task.started_at).total_seconds()
                task.result = TaskResult(
                    success=False,
                    output_path=self._extract_output_path(task),
                    error_message=error_msg,
                    duration_seconds=duration_seconds,
                )
                task.status = TaskStatus.CANCELLED if task.cancel_requested else TaskStatus.FAILED

            if task.status == TaskStatus.CANCELLED:
                if task.on_cancel:
                    self._queue_callback('cancel', task)
            elif task.on_error:
                self._queue_callback('error', task, error_msg)

        finally:
            with self._lock:
                self._active_count -= 1
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if possible."""
        callback_task: Optional[Task] = None
        should_invoke_cancel_fn = False
        cancel_fn: Optional[Callable[[], bool]] = None

        with self._lock:
            if task_id not in self._tasks:
                return False

            task = self._tasks[task_id]

            if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED):
                task.status = TaskStatus.CANCELLED
                task.cancel_requested = True
                callback_task = task if task.on_cancel else None
                logger.info(f"Task cancelled before execution: {task_id}")
            elif task.status == TaskStatus.RUNNING and task.cancel_fn:
                task.cancel_requested = True
                should_invoke_cancel_fn = True
                cancel_fn = task.cancel_fn
            else:
                return False

        if callback_task is not None:
            self._queue_callback('cancel', callback_task)
            return True

        if not should_invoke_cancel_fn:
            return True

        if should_invoke_cancel_fn and cancel_fn is not None:
            cancelled = bool(cancel_fn())
            if cancelled:
                logger.info(f"Task cancellation requested: {task_id}")
            return cancelled

        return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        with self._lock:
            return list(self._tasks.values())
    
    def get_pending_tasks(self) -> List[Task]:
        """Get pending/queued tasks"""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED)
            ]
    
    def get_active_tasks(self) -> List[Task]:
        """Get currently running tasks"""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.status == TaskStatus.RUNNING
            ]
    
    def get_completed_tasks(self) -> List[Task]:
        """Get completed tasks (success or failure)"""
        with self._lock:
            return [
                t for t in self._tasks.values()
                if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            ]
    
    def clear_completed(self):
        """Remove completed tasks from memory"""
        with self._lock:
            completed_ids = [
                tid for tid, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
            ]
            for tid in completed_ids:
                del self._tasks[tid]
        
        logger.info(f"Cleared {len(completed_ids)} completed tasks")
    
    def process_callbacks(self):
        """
        Process pending callbacks in the main thread.
        Call this periodically from the UI thread.
        """
        while True:
            try:
                callback_data = self._callback_queue.get_nowait()
                
                callback_type = callback_data[0]
                
                if callback_type == 'progress':
                    _, task, progress, message = callback_data
                    if task.on_progress:
                        task.on_progress(progress, message)
                
                elif callback_type == 'complete':
                    _, task = callback_data
                    if task.on_complete:
                        task.on_complete(task)
                
                elif callback_type == 'error':
                    _, task, error_msg = callback_data
                    if task.on_error:
                        task.on_error(task, error_msg)

                elif callback_type == 'cancel':
                    _, task = callback_data
                    if task.on_cancel:
                        task.on_cancel(task)

            except queue.Empty:
                break
    
    @property
    def queue_size(self) -> int:
        """Number of tasks waiting in queue"""
        return self._queue.qsize()
    
    @property
    def active_count(self) -> int:
        """Number of currently running tasks"""
        with self._lock:
            return self._active_count
    
    @property
    def is_running(self) -> bool:
        """Whether the queue is running"""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Whether queue intake is paused."""
        return self._paused

    def pause(self):
        """Pause worker intake for queued tasks."""
        self._paused = True
        logger.info("TaskQueue paused")

    def resume(self):
        """Resume worker intake for queued tasks."""
        self._paused = False
        logger.info("TaskQueue resumed")

    def toggle_pause(self) -> bool:
        """Toggle paused state and return new state."""
        self._paused = not self._paused
        logger.info("TaskQueue pause toggled: %s", self._paused)
        return self._paused


# Singleton instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue(max_concurrent: int = 2) -> TaskQueue:
    """Get or create the global task queue instance"""
    global _task_queue
    
    if _task_queue is None:
        _task_queue = TaskQueue(max_concurrent=max_concurrent)
        _task_queue.start()
    
    return _task_queue


def shutdown_task_queue():
    """Shutdown the global task queue"""
    global _task_queue
    
    if _task_queue is not None:
        _task_queue.stop()
        _task_queue = None

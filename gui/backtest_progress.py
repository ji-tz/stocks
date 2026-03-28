"""回测进度管理模块

提供回测任务的进度跟踪和SSE推送功能。
"""
import uuid
import threading
from typing import Dict, Any, Optional
from queue import Queue


class BacktestProgress:
    """回测进度管理器"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_task(self, task_id: Optional[str] = None) -> str:
        """创建新的回测任务
        
        Args:
            task_id: 任务ID，如果不提供则自动生成
            
        Returns:
            任务ID
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        with self._lock:
            self._tasks[task_id] = {
                'progress': 0,
                'total': 0,
                'status': 'pending',
                'cancelled': False,
                'error': None,
                'result': None,
                'queue': Queue()
            }
        
        return task_id
    
    def update_progress(self, task_id: str, current: int, total: int):
        """更新任务进度
        
        Args:
            task_id: 任务ID
            current: 当前进度
            total: 总进度
        """
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            if task.get('cancelled'):
                return
            task['progress'] = current
            task['total'] = total
            task['status'] = 'running'
            
            # 计算百分比
            percentage = int((current / total * 100)) if total > 0 else 0
            
            # 推送进度更新到队列
            task['queue'].put({
                'type': 'progress',
                'current': current,
                'total': total,
                'percentage': percentage
            })
    
    def set_result(self, task_id: str, result: Any):
        """设置任务结果
        
        Args:
            task_id: 任务ID
            result: 任务结果
        """
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            if task.get('cancelled'):
                return
            task['result'] = result
            task['status'] = 'completed'
            
            # 推送完成消息
            task['queue'].put({
                'type': 'completed',
                'result': result
            })
    
    def set_error(self, task_id: str, error: str):
        """设置任务错误
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        with self._lock:
            if task_id not in self._tasks:
                return
            
            task = self._tasks[task_id]
            if task.get('cancelled'):
                return
            task['error'] = error
            task['status'] = 'error'
            
            # 推送错误消息
            task['queue'].put({
                'type': 'error',
                'error': error
            })

    def cancel_task(self, task_id: str):
        """取消任务并通知前端停止等待。"""
        with self._lock:
            if task_id not in self._tasks:
                return

            task = self._tasks[task_id]
            if task.get('cancelled'):
                return

            task['cancelled'] = True
            task['status'] = 'cancelled'
            task['queue'].put({
                'type': 'cancelled'
            })

    def is_cancelled(self, task_id: str) -> bool:
        """判断任务是否已取消。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            return bool(task.get('cancelled'))
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典，如果任务不存在返回None
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_events(self, task_id: str):
        """获取任务事件流（生成器）
        
        Args:
            task_id: 任务ID
            
        Yields:
            事件字典
        """
        task = self.get_task(task_id)
        if not task:
            return
        
        queue = task['queue']
        
        while True:
            event = queue.get()
            yield event
            
            # 如果是完成或错误事件，结束流
            if event['type'] in ('completed', 'error', 'cancelled'):
                break
    
    def cleanup_task(self, task_id: str):
        """清理任务数据
        
        Args:
            task_id: 任务ID
        """
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]


# 全局进度管理器实例
_progress_manager = BacktestProgress()


def get_progress_manager() -> BacktestProgress:
    """获取全局进度管理器实例"""
    return _progress_manager

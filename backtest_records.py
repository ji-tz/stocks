"""回测记录管理模块

负责保存、读取和管理回测历史记录。
支持最多保存20条记录，采用FIFO（先进先出）策略。
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


class BacktestRecords:
    """回测记录管理器"""
    
    def __init__(self, storage_file: str = "data/backtest_records.json", max_records: int = 20):
        """初始化回测记录管理器
        
        Args:
            storage_file: 存储文件路径
            max_records: 最大记录数量（默认20条）
        """
        self.storage_file = storage_file
        self.max_records = max_records
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """确保存储目录存在"""
        storage_dir = os.path.dirname(self.storage_file)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
    
    def _load_records(self) -> List[Dict[str, Any]]:
        """从文件加载记录列表
        
        Returns:
            记录列表，如果文件不存在则返回空列表
        """
        if not os.path.exists(self.storage_file):
            return []
        
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('records', [])
        except (json.JSONDecodeError, IOError):
            return []
    
    def _save_records(self, records: List[Dict[str, Any]]) -> None:
        """保存记录列表到文件
        
        Args:
            records: 记录列表
        """
        data = {
            'records': records,
            'version': '1.0',
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_record(self, strategy: str, symbol: str, parameters: Dict[str, Any], 
                   result: Dict[str, Any]) -> str:
        """添加一条回测记录
        
        Args:
            strategy: 策略类型（sma/mean_cost/fixed_amount）
            symbol: 股票代码
            parameters: 策略参数
            result: 回测结果
            
        Returns:
            记录ID
        """
        records = self._load_records()
        
        # 生成记录ID（时间戳）
        record_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        
        # 构建记录
        record = {
            'id': record_id,
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy,
            'symbol': symbol,
            'parameters': parameters,
            'result': result
        }
        
        # 添加到记录列表头部
        records.insert(0, record)
        
        # 如果超过最大记录数，移除最旧的记录
        if len(records) > self.max_records:
            records = records[:self.max_records]
        
        # 保存到文件
        self._save_records(records)
        
        return record_id
    
    def get_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取记录列表
        
        Args:
            limit: 限制返回的记录数量，None表示返回全部
            
        Returns:
            记录列表（按时间倒序）
        """
        records = self._load_records()
        if limit is not None:
            return records[:limit]
        return records
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            记录详情，如果不存在则返回None
        """
        records = self._load_records()
        for record in records:
            if record['id'] == record_id:
                return record
        return None
    
    def delete_record(self, record_id: str) -> bool:
        """删除一条记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        records = self._load_records()
        new_records = [r for r in records if r['id'] != record_id]
        
        if len(new_records) < len(records):
            self._save_records(new_records)
            return True
        return False
    
    def clear_all(self) -> None:
        """清空所有记录"""
        self._save_records([])


# 全局实例
_records_manager = BacktestRecords()


def add_record(strategy: str, symbol: str, parameters: Dict[str, Any], 
               result: Dict[str, Any]) -> str:
    """添加回测记录（便捷函数）"""
    return _records_manager.add_record(strategy, symbol, parameters, result)


def get_records(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """获取回测记录列表（便捷函数）"""
    return _records_manager.get_records(limit)


def get_record(record_id: str) -> Optional[Dict[str, Any]]:
    """获取单条记录（便捷函数）"""
    return _records_manager.get_record(record_id)


def delete_record(record_id: str) -> bool:
    """删除记录（便捷函数）"""
    return _records_manager.delete_record(record_id)


def clear_all() -> None:
    """清空所有记录（便捷函数）"""
    _records_manager.clear_all()

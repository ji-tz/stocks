"""定投策略（Fixed Amount Investment Strategy）

每次投入固定金额购买股票，不考虑市场价格波动。
"""
import dataclasses
import math
from typing import Any


@dataclasses.dataclass
class FixedAmountDecision:
    """决策器：定投策略（Fixed Amount Investment）
    
    规则：
    - 每天投入固定金额购买股票
    - 根据当前价格计算能买多少股（需要是 lot_size 的整数倍）
    - 不考虑卖出，只持续买入
    
    属性：
        fixed_amount: 每次投入的固定金额（默认 1000 元）
    """
    
    fixed_amount: float = 1000.0
    
    def decide(self, open_price: float, close_price: float | None = None, 
               avg_cost: float = 0.0, shares: int = 0, date: Any = None):
        """决策是否交易
        
        定投策略：每天都买入固定金额的股票
        
        Args:
            open_price: 开盘价
            close_price: 收盘价（未使用）
            avg_cost: 平均成本（未使用）
            shares: 当前持股数（未使用）
            date: 日期（未使用）
            
        Returns:
            返回 'buy' 表示买入。具体购买股数由 calculate_shares() 方法计算。
        """
        # 定投策略：每天都买入
        return 'buy'
    
    def calculate_shares(self, price: float, lot_size: float = 100.0) -> float:
        """计算应该购买的股数
        
        根据固定金额和当前价格，计算能买多少份额（按 lot_size 粒度向下取整）。
        
        Args:
            price: 当前股价
            lot_size: 交易粒度（股票常用 100，基金可用 1 或 0.01）
            
        Returns:
            应该购买的股数/份额（lot_size 的整数倍）
        """
        if price <= 0 or lot_size <= 0:
            return 0.0
        
        # 计算能买多少股
        affordable_shares = self.fixed_amount / price
        
        # 向下取整到 lot_size 的整数倍
        lots = math.floor((affordable_shares + 1e-12) / lot_size)

        return round(lots * lot_size, 6)

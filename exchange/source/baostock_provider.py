import pandas as pd
import socket
from .base_provider import BaseProvider


class BaostockProvider(BaseProvider):
    def __init__(self, timeout_seconds: float = 8.0):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _normalize_date(value: str | None) -> str:
        """将日期统一为 YYYY-MM-DD，空值使用兜底范围。"""
        if value is None or str(value).strip() == "":
            return "1970-01-01"
        value = str(value)
        if "-" in value:
            return value
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"

    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            import baostock as bs
        except Exception as e:
            raise ImportError("baostock is required for BaostockProvider") from e

        if symbol.startswith("6"):
            code = f"sh.{symbol}"
        else:
            code = f"sz.{symbol}"

        sd = self._normalize_date(start_date)
        ed = self._normalize_date(end_date)
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(self.timeout_seconds)

        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise RuntimeError("baostock 登录失败")

            rs = bs.query_history_k_data_plus(code,
                                              "date,open,high,low,close,volume",
                                              start_date=sd,
                                              end_date=ed,
                                              frequency="d",
                                              adjustflag="2")

            if rs.error_code != "0":
                raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")

            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
        except TimeoutError as e:
            raise RuntimeError(f"baostock 请求超时({self.timeout_seconds}s)") from e
        except OSError as e:
            raise RuntimeError(f"baostock 网络异常: {e}") from e
        finally:
            try:
                bs.logout()
            except Exception:
                pass
            socket.setdefaulttimeout(old_timeout)

        if not data_list:
            raise RuntimeError("baostock: no data returned")

        df = pd.DataFrame(data_list, columns=rs.fields)
        df = df.rename(columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.loc[:, ["date", "open", "high", "low", "close", "volume"]]

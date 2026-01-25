import pandas as pd
from .base_provider import BaseProvider


class BaostockProvider(BaseProvider):
    def fetch(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            import baostock as bs
        except Exception as e:
            raise ImportError("baostock is required for BaostockProvider") from e

        if symbol.startswith("6"):
            code = f"sh.{symbol}"
        else:
            code = f"sz.{symbol}"

        lg = bs.login()
        if lg.error_code != "0":
            bs.logout()
            raise RuntimeError("baostock 登录失败")

        sd = start_date if "-" in start_date else f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        ed = end_date if "-" in end_date else f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        rs = bs.query_history_k_data_plus(code,
                                          "date,open,high,low,close,volume",
                                          start_date=sd,
                                          end_date=ed,
                                          frequency="d",
                                          adjustflag="3")

        if rs.error_code != "0":
            bs.logout()
            raise RuntimeError(f"baostock 查询失败: {rs.error_msg}")

        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        bs.logout()

        if not data_list:
            raise RuntimeError("baostock: no data returned")

        df = pd.DataFrame(data_list, columns=rs.fields)
        df = df.rename(columns={"date": "date", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.loc[:, ["date", "open", "high", "low", "close", "volume"]]

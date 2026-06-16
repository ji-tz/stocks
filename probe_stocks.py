import requests
import pandas as pd
import io

sources = [
    {
        "name": "网易CSV",
        "url": "https://quotes.money.163.com/service/chddata.html?code=0600900&start=20250101&end=20250110&fields=TOPEN;HIGH;LOW;TCLOSE;VOTURNOVER",
        "type": "csv"
    },
    {
        "name": "新浪日线",
        "url": "https://finance.sina.com.cn/realstock/company/sh600900/nc.shtml",
        "type": "access"
    },
    {
        "name": "腾讯日线kline",
        "url": "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh600900,day,2025-01-01,2025-01-10,640,qfq",
        "type": "json"
    },
    {
        "name": "东方财富kline",
        "url": "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600900&klt=101&fqt=1&beg=20250101&end=20250110&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56",
        "type": "json"
    },
    {
        "name": "stooq csv",
        "url": "https://stooq.com/q/d/l/?s=600900.cn&i=d",
        "type": "csv"
    }
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

results = []

for src in sources:
    try:
        response = requests.get(src['url'], headers=headers, timeout=15)
        status = "成功" if response.status_code == 200 else f"失败({response.status_code})"
        content_head = response.content[:20].hex()

        info = ""
        if response.status_code == 200:
            if src['type'] == "csv":
                try:
                    # 163 uses GBK, stooq might use UTF-8
                    enc = 'gbk' if '163' in src['url'] else 'utf-8'
                    df = pd.read_csv(io.BytesIO(response.content), encoding=enc)
                    info = f"行数: {len(df)}"
                except Exception as e:
                    info = f"CSV解析失败: {str(e)[:30]}"
            elif src['type'] == "json":
                try:
                    data = response.json()
                    info = "JSON解析成功"
                except Exception as e:
                    info = f"JSON解析失败: {str(e)[:30]}"
            elif src['type'] == "access":
                info = "可访问"

        results.append({
            "来源": src['name'],
            "状态": status,
            "头20字节": content_head,
            "备注/解析": info
        })
    except Exception as e:
        results.append({
            "来源": src['name'],
            "状态": "异常",
            "头20字节": "N/A",
            "备注/解析": str(e)[:50]
        })

df_res = pd.DataFrame(results)
print(df_res.to_markdown(index=False))

import numpy as np
from datetime import datetime, timedelta


def get_uniform_dates(num_days=60):

    # 获取当前日期
    today = datetime.today()

    today = datetime(2024, 12, 2)
    # 获取今年的元旦
    new_year = datetime(today.year, 1, 1)

    # 计算从元旦到今天的天数
    delta_days = (today - new_year).days + 1  # 加1包括今天

    if delta_days < num_days:
        # 如果天数不足60,进行差值
        dates = [new_year + timedelta(days=i % delta_days) for i in range(num_days)]
    else:
        # 均匀选择60天，确保今天被包含
        indices = np.linspace(0, delta_days - 1, num_days, dtype=int)
        dates = [new_year + timedelta(days=int(idx)) for idx in indices]
        # 确保今天在列表中
        if today not in dates:
            dates[-1] = today

    return sorted(dates)


# 打印结果
for idx, date in enumerate(get_uniform_dates()):
    print(date.strftime("%Y-%m-%d"), idx + 1)

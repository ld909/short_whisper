from datetime import datetime, timedelta


def next_time_point(current_time, chunk_split):

    # 开始时间是早上6点
    start_hour = 6
    # 结束时间是晚上22点
    end_hour = 22

    # 一共时间间隔
    time_gap = (end_hour - start_hour) / chunk_split

    # 四舍五入到最近的整数
    time_gap = round(time_gap)
    time_gap = int(time_gap)

    # 计算从6点开始的所有时间点,包括6点和22点
    all_time_points = [start_hour + i * time_gap for i in range(chunk_split + 1)]

    # 如果当前时间小于当前时间
    if current_time < datetime.now():
        # 返回当前时间的明早6点
        next_time = datetime.now().replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

    # 如果当前时间在所有时间点之前,除开最后一个时间点
    elif current_time > datetime.now() and current_time.hour in all_time_points[:-1]:
        next_time = current_time + timedelta(hours=time_gap)

    # 如果当前时间是最后一个时间点，设定下一个时间是明天早上6点
    elif current_time > datetime.now() and current_time.hour == all_time_points[-1]:
        next_time = current_time.replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

    return next_time


def test_next_time_point():
    # 测试用例1: 当前时间在所有时间点之前
    # current_time1 = datetime(2024, 5, 1, 8, 0, 0)
    # chunk_split1 = 4
    # expected_time1 = datetime(2024, 5, 9, 6, 0, 0)
    # assert next_time_point(current_time1, chunk_split1) == expected_time1

    # 测试用例2: 当前时间是最后一个时间点
    # current_time2 = datetime(2024, 6, 1, 22, 0, 0)
    # chunk_split2 = 4
    # expected_time2 = datetime(2024, 6, 2, 6, 0, 0)
    # assert next_time_point(current_time2, chunk_split2) == expected_time2

    # # 测试用例3: 当前时间小于当前实际时间
    current_time3 = datetime(2024, 6, 1, 6, 0, 0)
    chunk_split3 = 4
    expected_time3 = datetime(2024, 6, 1, 10, 0, 0)
    assert next_time_point(current_time3, chunk_split3) == expected_time3

    print("All tests passed!")


# 运行测试
test_next_time_point()

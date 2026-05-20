import re
from datetime import datetime

def preprocess_data(cls, v:str):
    clean_str = v.strip().replace("T", " ")
    if re.match(r'^\d{8}', clean_str):
        clean_str = f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]} {clean_str[8:]}"
    datetimee = clean_str.split(" ")
    date, time = datetimee[0], datetimee[-1]

    # обработка даты
    date_parts = date.split("-")
    y,m,d = date_parts[0], date_parts[1], date_parts[2]

    if int(m) > 12:
        m,d=d,m
    
    dt = datetime(int(y), int(m), int(d))
    return dt.strftime(f'%Y-%m-%d {time}')



test_times = [
    "2022-12-23 05:56:06",
    "2021-06-09 20:59:18",
    "2022-11-24 17:07:20",
    "2022-01-21T09:09:17",
    "20220317 15:49:17",
    "19800713T205307",
    "20220605 060755",
    "1993-12-14 05:44:30",
    "2022-13-01 11:16:56",
    "2010-30-02 05:56:30",
]

for time_value in test_times:
    print("Было:", time_value)

    try:
        result = preprocess_data(None, time_value)
        print("Стало:", result)

    except Exception as error:
        print("Ошибка:", error)

    print("-" * 40)
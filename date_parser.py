import datetime
import re

weekday_ko = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}


def get_date_for_weekday(offset_weeks, weekday):
    today = datetime.date.today()
    base = today + datetime.timedelta(days=(7 * offset_weeks - today.weekday()))
    return base + datetime.timedelta(days=weekday)


def expand_range(start_wd, end_wd):
    start = weekday_ko[start_wd]
    end = weekday_ko[end_wd]
    return [d for d in range(start, end + 1)] if start <= end else []


def extract_dates_from_text(text):
    today = datetime.date.today()
    dates = set()
    time_filter = None

    # 0. time filter 감지
    if "저녁" in text:
        time_filter = "evening"
    elif "점심" in text:
        time_filter = "lunch"

    # 표현 매핑 정의
    prefix_map = {
        "다다음주": 2, "다담주": 2, "2주뒤": 2, "2주 뒤": 2, "2주후": 2, "2주 후": 2,
        "다음주": 1, "담주": 1, "1주뒤": 1, "1주 뒤": 1, "1주후": 1, "1주 후": 1,
        "이번주": 0, "0주뒤": 0, "0주 뒤": 0
    }

    # 1. 5/26 형식
    md_pattern = re.findall(r"\b(\d{1,2})/(\d{1,2})\b", text)
    for month, day in md_pattern:
        try:
            dt = datetime.date(today.year, int(month), int(day))
            dates.add(dt)
        except:
            continue

    # 2. 주차 단어 + 요일들 (붙은/쉼표형/범위형 모두)
    for prefix, offset in prefix_map.items():
        if prefix in text:
            after = text.split(prefix)[-1]
            match = re.search(rf"{prefix}\s*([월화수목금토일])부터\s*([월화수목금토일])까지", text)
            if match:
                wd1, wd2 = match.groups()
                for i in expand_range(wd1, wd2):
                    dates.add(get_date_for_weekday(offset, i))
            else:
                parts = re.findall(r"[월화수목금토일]", after)
                for p in parts:
                    if p in weekday_ko:
                        dates.add(get_date_for_weekday(offset, weekday_ko[p]))
            if not re.search(r"[월화수목금토일]", after):
                for i in range(7):
                    dates.add(get_date_for_weekday(offset, i))

    # 3. 복수 날짜 쉼표 구분: 5/26, 5/27, 5/28
    if "," in text:
        md_multi = re.findall(r"(\d{1,2})/(\d{1,2})", text)
        for month, day in md_multi:
            try:
                dt = datetime.date(today.year, int(month), int(day))
                dates.add(dt)
            except:
                continue

    return sorted([d.isoformat() for d in dates]), time_filter

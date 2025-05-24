import datetime
import re
import calendar

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
    keyword_filter = None
    available_only = "한가" in text
    weekday_filter = []

    # 시간 필터
    if "저녁" in text:
        time_filter = "evening"
    elif "점심" in text:
        time_filter = "lunch"

    # 키워드 필터 (골프, 회의 등 추출)
    m = re.search(r"(전체)?\\s*(골프|회의|미팅|저녁|점심)", text)
    if m:
        word = m.group(2)
        if word not in ["저녁", "점심"]:
            keyword_filter = word

    # 월 전체
    m = re.search(r"(\\d{1,2})월", text)
    if m:
        month = int(m.group(1))
        if "전체" in text or "일정" in text:
            year = today.year
            last_day = calendar.monthrange(year, month)[1]
            for day in range(1, last_day + 1):
                dates.add(datetime.date(year, month, day))

    # 월/일 형식
    md_pattern = re.findall(r"\\b(\\d{1,2})/(\\d{1,2})\\b", text)
    for month, day in md_pattern:
        try:
            dt = datetime.date(today.year, int(month), int(day))
            dates.add(dt)
        except:
            continue

    # 주차 표현
    prefix_map = {
        "다다음주": 2, "다담주": 2, "다음다음주": 2,
        "다음주": 1, "담주": 1, "1주뒤": 1, "1주 뒤": 1, "1주후": 1, "1주 후": 1,
        "이번주": 0, "0주뒤": 0
    }

    for prefix, offset in prefix_map.items():
        if prefix in text:
            after = text.split(prefix)[-1]
            # 범위 요일
            match = re.search(rf"{prefix}\\s*([월화수목금토일])부터\\s*([월화수목금토일])까지", text)
            if match:
                wd1, wd2 = match.groups()
                for i in expand_range(wd1, wd2):
                    dates.add(get_date_for_weekday(offset, i))
            else:
                parts = re.findall(r"[월화수목금토일]", after)
                for p in parts:
                    if p in weekday_ko:
                        dates.add(get_date_for_weekday(offset, weekday_ko[p]))
            # 요일이 없을 경우 전체 주
            if not re.search(r"[월화수목금토일]", after):
                for i in range(7):
                    dates.add(get_date_for_weekday(offset, i))

    # 평일/주말 필터링
    if "평일" in text:
        weekday_filter = [0, 1, 2, 3, 4]
    elif "주말" in text:
        weekday_filter = [5, 6]

    # 복수 날짜 쉼표 처리
    if "," in text:
        md_multi = re.findall(r"(\\d{1,2})/(\\d{1,2})", text)
        for month, day in md_multi:
            try:
                dt = datetime.date(today.year, int(month), int(day))
                dates.add(dt)
            except:
                continue

    final_dates = [d for d in sorted(dates) if not weekday_filter or d.weekday() in weekday_filter]
    return [d.isoformat() for d in final_dates], time_filter, keyword_filter, available_only, weekday_filter

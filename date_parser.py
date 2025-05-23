import datetime
import re

# 지원하는 한글 요일 약어 매핑
weekday_ko = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

# next_week 또는 this_week 기준 계산

def get_date_for_weekday(offset_weeks, weekday):
    today = datetime.date.today()
    base = today + datetime.timedelta(days=(7 * offset_weeks - today.weekday()))
    return base + datetime.timedelta(days=weekday)


def extract_dates_from_text(text):
    today = datetime.date.today()
    dates = set()

    # 1. 5/26 형식
    md_pattern = re.findall(r"\b(\d{1,2})/(\d{1,2})\b", text)
    for month, day in md_pattern:
        try:
            dt = datetime.date(today.year, int(month), int(day))
            dates.add(dt)
        except:
            continue

    # 2. '다음주 월화수' / '이번주 월, 화'
    for prefix, offset in [("다음주", 1), ("담주", 1), ("이번주", 0)]:
        if prefix in text:
            sub = text.split(prefix)[-1]  # 이후 문자열만 파싱
            for char in sub:
                if char in weekday_ko:
                    dates.add(get_date_for_weekday(offset, weekday_ko[char]))

    # 3. '다음주 월', '이번주 화' 등 쉼표 패턴
    for prefix, offset in [("다음주", 1), ("담주", 1), ("이번주", 0)]:
        matches = re.findall(rf"{prefix}[\s]*([\w, ]+)", text)
        for match in matches:
            parts = re.split(r"[\s,]+", match)
            for p in parts:
                p = p.strip()
                if p in weekday_ko:
                    dates.add(get_date_for_weekday(offset, weekday_ko[p]))

    # 4. 정렬 및 중복 제거
    sorted_dates = sorted(dates)
    return [d.isoformat() for d in sorted_dates]

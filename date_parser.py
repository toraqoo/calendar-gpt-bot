import re
from datetime import datetime, timedelta
import calendar

KST = timedelta(hours=9)

def get_week_range(target_date):
    start = target_date - timedelta(days=target_date.weekday())
    end = start + timedelta(days=6)
    return start, end

def get_month_range(year, month):
    start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day)
    return start, end

def extract_dates_from_text(text, today=None):
    if today is None:
        today = datetime.now() + KST

    text = text.lower()
    dates = []
    time_filter = None
    keyword_filter = None
    find_available = False
    weekdays_kor = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6}

    if '점심' in text:
        time_filter = 'lunch'
    elif '저녁' in text:
        time_filter = 'evening'

    keyword_match = re.search(r"(골프|데이트|회식|미팅|회의|병원|약속|식사)", text)
    if keyword_match:
        keyword_filter = keyword_match.group(1)

    if '한가' in text or '비는 날' in text:
        find_available = True

    if match := re.search(r'(\d{1,2})월', text):
        month = int(match.group(1))
        year = today.year if month >= today.month else today.year + 1
        start, end = get_month_range(year, month)
        delta = (end - start).days + 1
        dates = [start + timedelta(days=i) for i in range(delta)]
    elif any(key in text for key in ['다다다음주', '다다담주', '3주뒤', '3주 후', '3주후', '3주 뒤']):
        base = today + timedelta(weeks=3)
        start, _ = get_week_range(base)
        dates = [start + timedelta(days=i) for i in range(7)]
    elif any(key in text for key in ['다다음주', '다담주', '2주뒤', '2주 후', '2주후', '2주 뒤']):
        base = today + timedelta(weeks=2)
        start, _ = get_week_range(base)
        dates = [start + timedelta(days=i) for i in range(7)]
    elif any(key in text for key in ['다음주', '담주', '1주뒤', '1주 후', '1주후', '1주 뒤']):
        base = today + timedelta(weeks=1)
        start, _ = get_week_range(base)
        dates = [start + timedelta(days=i) for i in range(7)]
    elif any(key in text for key in ['이번주', '금주']):
        start, _ = get_week_range(today)
        dates = [start + timedelta(days=i) for i in range(7)]
    elif match := re.findall(r'(\d{1,2})[./](\d{1,2})', text):
        for m, d in match:
            month = int(m)
            day = int(d)
            year = today.year if month >= today.month else today.year + 1
            try:
                dates.append(datetime(year, month, day))
            except ValueError:
                continue

    if '평일' in text:
        dates = [d for d in dates if d.weekday() < 5]
    elif '주말' in text:
        dates = [d for d in dates if d.weekday() >= 5]
    elif any(day in text for day in weekdays_kor) and not re.search(r'\d{1,2}월', text):
        if dates:
            days = [weekdays_kor[day] for day in weekdays_kor if day in text]
            dates = [d for d in dates if d.weekday() in days]

    return {
        'dates': sorted(list(set(dates))),
        'time_filter': time_filter,
        'keyword_filter': keyword_filter,
        'find_available': find_available,
    }

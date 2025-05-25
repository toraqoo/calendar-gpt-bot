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

    # ✅ 텍스트 정제
    text = text.lower().strip()
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

    dates = set()
    time_filter = None
    keyword_filter = None
    find_available = False
    weekdays_kor = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6}

    # 시간대 필터
    if '점심' in text:
        time_filter = 'lunch'
    elif '저녁' in text:
        time_filter = 'evening'

    # 키워드 필터
    keyword_match = re.search(r"(골프|데이트|회식|미팅|회의|병원|약속|식사)", text)
    if keyword_match:
        keyword_filter = keyword_match.group(1)

    if '한가' in text or '비는 날' in text:
        find_available = True

    expressions = [text]
    for exp in expressions:
        exp = exp.strip()

        # ✅ 상대 날짜 표현 (긴 표현 → 짧은 표현 순서)
        if '내일모레' in exp or '낼모레' in exp:
            dates.add((today + timedelta(days=2)).date())
            continue
        if '내일' in exp and '모레' not in exp:
            dates.add((today + timedelta(days=1)).date())
            continue
        if '낼' in exp and '모레' not in exp and '내일' not in exp:
            dates.add((today + timedelta(days=1)).date())
            continue
        if '모레' in exp:
            dates.add((today + timedelta(days=2)).date())
            continue
        if '글피' in exp:
            dates.add((today + timedelta(days=3)).date())
            continue
        if '오늘' in exp:
            dates.add(today.date())
            continue

        # 단어 기반 상대일
        word_day_map = {
            '하루': 1, '이틀': 2, '사흘': 3, '나흘': 4, '닷새': 5, '엿새': 6, '일주일': 7
        }
        for word, offset in word_day_map.items():
            if f'{word} 뒤' in exp or f'{word} 후' in exp:
                dates.add((today + timedelta(days=offset)).date())
                break
            if f'{word} 전' in exp or f'{word} 앞' in exp:
                dates.add((today - timedelta(days=offset)).date())
                break

        # 숫자 기반 상대일
        if match := re.search(r'(\d+)[일\s]*(뒤|후)', exp):
            offset = int(match.group(1))
            dates.add((today + timedelta(days=offset)).date())
        elif match := re.search(r'(\d+)[일\s]*(전|앞)', exp):
            offset = int(match.group(1))
            dates.add((today - timedelta(days=offset)).date())

        # 월 전체
        elif match := re.search(r'(\d{1,2})월', exp):
            month = int(match.group(1))
            year = today.year if month >= today.month else today.year + 1
            start, end = get_month_range(year, month)
            for i in range((end - start).days + 1):
                dates.add((start + timedelta(days=i)).date())

        # 주 단위
        elif any(key in exp for key in ['다다다음주', '다다담주', '3주뒤', '3주 후']):
            base = today + timedelta(weeks=3)
            start, _ = get_week_range(base)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())
        elif any(key in exp for key in ['다다음주', '다담주', '2주뒤', '2주 후']):
            base = today + timedelta(weeks=2)
            start, _ = get_week_range(base)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())
        elif any(key in exp for key in ['다음주', '담주', '1주뒤', '1주 후']):
            base = today + timedelta(weeks=1)
            start, _ = get_week_range(base)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())
        elif any(key in exp for key in ['이번주', '금주']):
            start, _ = get_week_range(today)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())

        # 5/26, 6.11 등
        elif match := re.findall(r'(\d{1,2})[./](\d{1,2})', exp):
            for m, d in match:
                month = int(m)
                day = int(d)
                year = today.year if month >= today.month else today.year + 1
                try:
                    dates.add(datetime(year, month, day).date())
                except ValueError:
                    continue

    # 평일/주말/요일 필터
    if '평일' in text:
        dates = {d for d in dates if datetime.combine(d, datetime.min.time()).weekday() < 5}
    elif '주말' in text:
        dates = {d for d in dates if datetime.combine(d, datetime.min.time()).weekday() >= 5}
    elif any(day in text for day in weekdays_kor) and not re.search(r'\d{1,2}월', text):
        days = [weekdays_kor[day] for day in weekdays_kor if day in text]
        dates = {d for d in dates if datetime.combine(d, datetime.min.time()).weekday() in days}

    return {
        'dates': sorted(dates),
        'time_filter': time_filter,
        'keyword_filter': keyword_filter,
        'find_available': find_available,
    }

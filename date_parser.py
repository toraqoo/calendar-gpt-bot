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
    print(f"[DEBUG] final cleaned text = {repr(text)}")

    dates = set()
    time_filter = None
    keyword_filter = None
    find_available = False
    weekday_filter = None  # ← 최종 복합 포인트

    weekdays_kor = {'월': 0, '화': 1, '수': 2, '목': 3, '금': 4, '토': 5, '일': 6}

    # 시간대 필터
    if 'uc810uc2ec' in text:
        time_filter = 'lunch'
    elif 'uc800uc5b4' in text:
        time_filter = 'evening'

    # 균정 필터
    keyword_match = re.search(r"(\uace0\uc2a4|\ub370\uc774\ud2b8|\ud68c신|\ubbf8팅|\ud68c의|\ubcd1원|\uc57d속|\uc2dd사)", text)
    if keyword_match:
        keyword_filter = keyword_match.group(1)

    if 'ud55cuac00' in text or 'ube44ub294 ub0a0' in text:
        find_available = True

    if 'ud3c9uc77c' in text:
        weekday_filter = 'weekday'
    elif 'uc8fcub9d0' in text:
        weekday_filter = 'weekend'

    expressions = [text]
    for exp in expressions:
        exp = exp.strip()
        print(f"[DEBUG] 번서 중 exp: {repr(exp)}")

        if 'ub0b4uc77cuba54ub808' in exp or 'ub0b4ubaa8ub808' in exp:
            print("[MATCH] 내uc77cuba54ub808")
            dates.add((today + timedelta(days=2)).date())
            continue
        if 'ub0b4uc77c' in exp:
            print("[MATCH] 내uc77c")
            dates.add((today + timedelta(days=1)).date())
            continue
        if 'ub0b4' in exp and 'ub0b4uc77c' not in exp and 'ubaa8ub808' not in exp:
            print("[MATCH] 내")
            dates.add((today + timedelta(days=1)).date())
            continue
        if 'ubaa8ub808' in exp:
            print("[MATCH] 모ub808")
            dates.add((today + timedelta(days=2)).date())
            continue
        if '글피' in exp:
            print("[MATCH] 글피")
            dates.add((today + timedelta(days=3)).date())
            continue
        if 'uc624ub298' in exp:
            print("[MATCH] 오ub298")
            dates.add(today.date())
            continue

        word_day_map = {
            'ud558ub8e8': 1, 'uc774틀': 2, 'uc0acud74c': 3, 'ub098ud74c': 4, 'ub2e4uc0ac': 5, 'uc5bf사': 6, 'uc77cuc8fc일': 7
        }
        for word, offset in word_day_map.items():
            if f'{word} 드이' in exp or f'{word} 후' in exp:
                print(f"[MATCH] 단어기반 +{offset}일")
                dates.add((today + timedelta(days=offset)).date())
                break
            if f'{word} 전' in exp or f'{word} 앞' in exp:
                print(f"[MATCH] 단어기반 -{offset}일")
                dates.add((today - timedelta(days=offset)).date())
                break

        if match := re.search(r'(\d+)[\uc77c\s]*(\ub4dc\uc774|\ud6c4)', exp):
            offset = int(match.group(1))
            print(f"[MATCH] 숫자기반 +{offset}일")
            dates.add((today + timedelta(days=offset)).date())
        elif match := re.search(r'(\d+)[\uc77c\s]*(\uc804|\uc55e)', exp):
            offset = int(match.group(1))
            print(f"[MATCH] 숫자기반 -{offset}일")
            dates.add((today - timedelta(days=offset)).date())

        elif match := re.search(r'(\d{1,2})\uc6d4', exp):
            print(f"[MATCH] \uc6d4 \uc804체 \ucc98리")
            month = int(match.group(1))
            year = today.year if month >= today.month else today.year + 1
            start, end = get_month_range(year, month)
            for i in range((end - start).days + 1):
                dates.add((start + timedelta(days=i)).date())

        elif any(key in exp for key in ['ub2e4ub2e4ub2e4uc74c주', 'ub2e4ub2e4ub2bc주', '3주ub4dc', '3주 후']):
            print("[MATCH] 3주 후")
            base = today + timedelta(weeks=3)
            start, _ = get_week_range(base)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())

        elif any(key in exp for key in ['ub2e4ub2bc주', 'ub2e4ub2f0주', '2주ub4dc', '2주 후']):
            print("[MATCH] 2주 후")
            base = today + timedelta(weeks=2)
            start, _ = get_week_range(base)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())

        elif any(key in exp for key in ['ub2f4주', 'ub2bc주', '1주ub4dc', '1주 후']):
            print("[MATCH] 담주")
            base = today + timedelta(weeks=1)
            start, _ = get_week_range(base)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())

        elif any(key in exp for key in ['uc774번주', '\uae08주']):
            print("[MATCH] 이번주")
            start, _ = get_week_range(today)
            for i in range(7):
                dates.add((start + timedelta(days=i)).date())

        elif match := re.findall(r'(\d{1,2})[./](\d{1,2})', exp):
            for m, d in match:
                print(f"[MATCH] \ub0a0짜 \ud328턴 {m}/{d}")
                month = int(m)
                day = int(d)
                year = today.year if month >= today.month else today.year + 1
                try:
                    dates.add(datetime(year, month, day).date())
                except ValueError:
                    continue

    if not dates:
        print("[WARN] \ub0a0짜 \uc778식 \uc2e4패, \ubc18환할 \ub0a0짜 없음")

    return {
        'dates': sorted(dates),
        'time_filter': time_filter,
        'keyword_filter': keyword_filter,
        'find_available': find_available,
        'weekday_filter': weekday_filter  # ← 참고할 값
    }

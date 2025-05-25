import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, time, date
from collections import defaultdict

# 구글 인증 설정
credentials_info = json.loads(os.environ['GOOGLE_CREDENTIALS_JSON'])
credentials = service_account.Credentials.from_service_account_info(credentials_info)
service = build('calendar', 'v3', credentials=credentials)
CALENDAR_ID = 'mk@bonanza-factory.co.kr'

# ✅ date → datetime 변환 함수
def normalize_dates(dates):
    result = []
    for d in dates:
        if isinstance(d, datetime):
            result.append(d)
        elif isinstance(d, date):  # datetime.date (but not datetime)
            result.append(datetime.combine(d, time.min))  # 00:00
    return result

# 일정 가져오기
def get_events(dates):
    date_times = normalize_dates(dates)
    if not date_times:
        return []

    start_date = min(date_times).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
    end_date = (max(date_times) + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_date,
        timeMax=end_date,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    items = events_result.get('items', [])
    events = []
    for event in items:
        if 'dateTime' not in event['start']:
            continue
        start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
        events.append({
            'start': start,
            'end': end,
            'summary': event.get('summary', '(제목 없음)')
        })
    return events

# 필터링
def filter_events(events, time_filter=None, keyword_filter=None):
    result = []
    for e in events:
        start_time = e['start'].time()
        title = e['summary']
        if time_filter == 'lunch' and not time(11, 0) <= start_time <= time(14, 0):
            continue
        if time_filter == 'evening' and not time(17, 0) <= start_time <= time(20, 0):
            continue
        if keyword_filter and keyword_filter not in title:
            continue
        result.append(e)
    return result

# 한가한 날 찾기
def find_available_days(events, target_dates, time_filter=None):
    busy_days = set()
    for e in filter_events(events, time_filter=time_filter):
        busy_days.add(e['start'].date())
    available = [d for d in target_dates if isinstance(d, datetime) and d.date() not in busy_days or isinstance(d, date) and d not in busy_days]
    return available

# 주차 라벨 포맷
def format_week_label(week_start):
    month = week_start.month
    week_of_month = (week_start.day - 1) // 7 + 1
    return f"[ {month}M{week_of_month}W : {week_start.strftime('%m/%d')} ~ {(week_start + timedelta(days=6)).strftime('%m/%d')} ]"

# ✅ 이모지 붙이는 함수
def attach_emoji_to_event(summary: str) -> str:
    emoji_map = {
        "회의": "📝",
        "점심": "🍽️",
        "저녁": "🍽️",
        "워크샵": "🧠",
        "골프": "⛳",
        "SMS": "🎭"
    }
    for keyword, emoji in emoji_map.items():
        if keyword in summary:
            return f"{emoji} {summary}"
    return summary

# ✅ 일정 출력 (이모지 포함)
def format_event_list(events):
    grouped_by_week = defaultdict(lambda: defaultdict(list))
    for e in sorted(events, key=lambda x: x['start']):
        date_key = e['start'].date()
        week_start = date_key - timedelta(days=date_key.weekday())
        grouped_by_week[week_start][date_key].append(e)

    lines = []
    for week_start in sorted(grouped_by_week):
        lines.append(f"\n🗓️ {format_week_label(week_start)}")
        for date in sorted(grouped_by_week[week_start]):
            lines.append("")
            date_str = date.strftime('%m/%d(%a)').replace('Mon','월').replace('Tue','화').replace('Wed','수') \
                .replace('Thu','목').replace('Fri','금').replace('Sat','토').replace('Sun','일')
            lines.append(f"{date_str}")
            for e in grouped_by_week[week_start][date]:
                start = e['start']
                end = e['end']
                duration = (end - start).total_seconds() / 3600
                duration_str = f"{duration:.1f}".rstrip("0").rstrip(".")
                time_str = f"{start.strftime('%H:%M')}~{end.strftime('%H:%M')}({duration_str}h)"
                summary_with_emoji = attach_emoji_to_event(e['summary'])
                lines.append(f"- {time_str}: {summary_with_emoji}")
    return "\n".join(lines)

# 한가한 날 포맷
def format_available_days(dates, time_filter=None):
    label = "점심시간(11~14시)" if time_filter == 'lunch' else "저녁시간(17~20시)" if time_filter == 'evening' else "비어 있음"
    grouped_by_week = defaultdict(list)
    for d in sorted(dates):
        week_start = d - timedelta(days=d.weekday())
        grouped_by_week[week_start].append(d)

    lines = []
    for week_start in sorted(grouped_by_week):
        lines.append(f"\n🗓️ {format_week_label(week_start)}")
        for d in grouped_by_week[week_start]:
            day_str = d.strftime('%m/%d(%a)').replace('Mon','월').replace('Tue','화').replace('Wed','수') \
                .replace('Thu','목').replace('Fri','금').replace('Sat','토').replace('Sun','일')
            lines.append(f"- {day_str} {label}")
    return "\n".join(lines)

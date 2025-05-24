# gcal.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, time

SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CALENDAR_ID = 'primary'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('calendar', 'v3', credentials=credentials)

def get_events(dates):
    start_date = min(dates).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
    end_date = (max(dates) + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_date,
        timeMax=end_date,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = []
    for event in events_result.get('items', []):
        if 'dateTime' not in event['start']:
            continue  # 하루종일 일정은 제외

        start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
        events.append({
            'start': start,
            'end': end,
            'summary': event.get('summary', '(제목 없음)')
        })

    return events

def filter_events(events, time_filter=None, keyword_filter=None):
    result = []
    for e in events:
        start_time = e['start'].time()
        title = e['summary']

        if time_filter == 'lunch' and not time(11, 0) <= start_time <= time(14, 0):
            continue
        if time_filter == 'evening' and not time(18, 0) <= start_time <= time(21, 0):
            continue
        if keyword_filter and keyword_filter not in title:
            continue
        result.append(e)
    return result

def find_available_days(events, target_dates, time_filter=None):
    busy_days = set()
    for e in filter_events(events, time_filter=time_filter):
        busy_days.add(e['start'].date())
    available = [d for d in target_dates if d.date() not in busy_days]
    return available

def format_event_list(events):
    seen = set()
    lines = []
    for e in sorted(events, key=lambda x: x['start']):
        start = e['start']
        end = e['end']
        title = e['summary']
        duration = end - start
        key = (start, end, title)
        if key in seen:
            continue
        seen.add(key)
        day_str = start.strftime('%y/%m/%d(%a)').replace('Mon', '월').replace('Tue', '화').replace('Wed', '수') \
            .replace('Thu', '목').replace('Fri', '금').replace('Sat', '토').replace('Sun', '일')
        time_str = f"{start.strftime('%H:%M')}~{end.strftime('%H:%M')}({int(duration.total_seconds() // 3600)}h)"
        lines.append(f"\U0001F4C5 {day_str}\n- {time_str}: {title}")
    return "\n\n".join(lines)

def format_available_days(dates):
    lines = []
    for d in sorted(dates):
        day_str = d.strftime('%y/%m/%d(%a)').replace('Mon', '월').replace('Tue', '화').replace('Wed', '수') \
            .replace('Thu', '목').replace('Fri', '금').replace('Sat', '토').replace('Sun', '일')
        lines.append(f"✅ {day_str} 점심시간(11~14시) 비어 있음")
    return "\n".join(lines)

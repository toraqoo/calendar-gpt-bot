from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import datetime

def get_calendar_service():
    creds = Credentials(
        None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )
    return build("calendar", "v3", credentials=creds)

def resolve_date_string(date_str):
    today = datetime.date.today()
    if date_str == "today":
        return today
    elif date_str == "tomorrow":
        return today + datetime.timedelta(days=1)
    elif date_str == "next_week_start":
        return today + datetime.timedelta(days=(7 - today.weekday()))  # 다음주 월요일
    elif date_str.startswith("next_week_day_"):  # next_week_day_0~6 (월~일)
        weekday = int(date_str.split("_")[-1])
        base = today + datetime.timedelta(days=(7 - today.weekday()))
        return base + datetime.timedelta(days=weekday)
    else:
        # try to parse ISO format
        try:
            return datetime.date.fromisoformat(date_str)
        except:
            raise ValueError(f"날짜 '{date_str}'를 해석할 수 없습니다.")

def get_events_by_filter(parsed):
    service = get_calendar_service()
    start = parsed.get("date_range", {}).get("start")
    end = parsed.get("date_range", {}).get("end")
    time_filter = parsed.get("time_filter", None)
    keyword = parsed.get("keyword_filter")

    try:
        start_date = resolve_date_string(start)
        end_date = resolve_date_string(end)
    except Exception as e:
        raise ValueError(f"날짜 해석 실패: {e}")

    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)
    timeMin = start_dt.isoformat() + 'Z'
    timeMax = end_dt.isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=timeMin,
        timeMax=timeMax,
        maxResults=50,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # 시간 필터링
    if time_filter:
        def in_range(event):
            dt = event['start'].get('dateTime')
            if not dt:
                return False
            hour = int(dt[11:13])
            if time_filter == "evening":
                return 18 <= hour <= 22
            elif time_filter == "morning":
                return 6 <= hour < 12
            elif time_filter == "afternoon":
                return 12 <= hour < 18
            return True
        events = list(filter(in_range, events))

    # 키워드 필터링
    if keyword and isinstance(keyword, str):
        events = [e for e in events if keyword.lower() in e.get('summary', '').lower()]

    return events

def format_event_list(events):
    result = []
    for e in events:
        start_dt = e['start'].get('dateTime', e['start'].get('date'))
        try:
            dt = datetime.datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d (%a) %H:%M")
        except:
            date_str = start_dt
        result.append(f"🗓 {date_str} - {e.get('summary', '제목 없음')}")
    return "\n".join(result)

def get_today_events():
    today = datetime.date.today()
    return get_events_by_filter({
        "action": "get_schedule",
        "date_range": {
            "start": today.isoformat(),
            "end": today.isoformat()
        }
    })


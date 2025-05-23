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

def get_today_events():
    service = get_calendar_service()
    now = datetime.datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=today_start,
        timeMax=today_end,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    return events

def get_tomorrow_events():
    service = get_calendar_service()
    tomorrow = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    start = tomorrow.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
    end = tomorrow.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    return events

def get_nextweek_evening_free_days():
    service = get_calendar_service()
    today = datetime.date.today()
    start = today + datetime.timedelta(days=(7 - today.weekday()))  # 다음주 월요일
    evening_free = []

    for i in range(7):  # 월~일
        day = start + datetime.timedelta(days=i)
        t_start = datetime.datetime.combine(day, datetime.time(18, 0)).isoformat() + 'Z'
        t_end = datetime.datetime.combine(day, datetime.time(23, 0)).isoformat() + 'Z'
        events = service.events().list(
            calendarId='primary',
            timeMin=t_start,
            timeMax=t_end,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
        
        if not events:
            evening_free.append(day.strftime("%Y-%m-%d (%a)"))

    return evening_free

def get_events_by_filter(parsed):
    service = get_calendar_service()
    start = parsed.get("date_range", {}).get("start")
    end = parsed.get("date_range", {}).get("end")
    time_filter = parsed.get("time_filter", None)
    keyword = parsed.get("keyword_filter", "").lower()

    if not start or not end:
        raise ValueError("start/end 날짜가 누락됐습니다.")

    t_start = datetime.datetime.fromisoformat(start)
    t_end = datetime.datetime.fromisoformat(end)
    t_start = t_start.replace(hour=0, minute=0, second=0)
    t_end = t_end.replace(hour=23, minute=59, second=59)

    timeMin = t_start.isoformat() + 'Z'
    timeMax = t_end.isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=timeMin,
        timeMax=timeMax,
        maxResults=50,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # 시간 필터링 (optional)
    if time_filter:
        def in_time_range(event):
            dt = event['start'].get('dateTime')
            if not dt:
                return False
            hour = int(dt[11:13])
            if time_filter == "evening":
                return 18 <= hour <= 22
            if time_filter == "morning":
                return 6 <= hour <= 12
            if time_filter == "afternoon":
                return 12 <= hour <= 18
            return True
        events = list(filter(in_time_range, events))

    # 키워드 필터링
    if keyword:
        events = [e for e in events if keyword in e.get('summary', '').lower()]

    return events

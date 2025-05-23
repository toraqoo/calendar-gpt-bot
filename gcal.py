from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import datetime
import re

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
    weekday_map_ko = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    weekday_map_en = {
        "monday": 0, "tuesday": 1, "wednesday": 2,
        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
    }

    if not date_str:
        raise ValueError("날짜 문자열이 비어 있음")

    # '5/26(월)' 같은 날짜 표현 대응
    try:
        date_str = re.sub(r"[\(\)\s]", "", date_str)
        if re.match(r"\d{1,2}/\d{1,2}", date_str):
            month, day = map(int, date_str.split("/"))
            return datetime.date(today.year, month, day)
    except:
        pass

    # '다음주 월', '다다음주 수' 등의 표현 처리
    try:
        if date_str.startswith("다음주"):
            dow = date_str.replace("다음주", "").strip()
            base = today + datetime.timedelta(days=(7 - today.weekday()))
            weekday = weekday_map_ko.get(dow) or weekday_map_en.get(dow.lower())
            if weekday is not None:
                return base + datetime.timedelta(days=weekday)
        if date_str.startswith("다다음주"):
            dow = date_str.replace("다다음주", "").strip()
            base = today + datetime.timedelta(days=(14 - today.weekday()))
            weekday = weekday_map_ko.get(dow) or weekday_map_en.get(dow.lower())
            if weekday is not None:
                return base + datetime.timedelta(days=weekday)
    except:
        pass

    if date_str == "today":
        return today
    if date_str == "tomorrow":
        return today + datetime.timedelta(days=1)

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

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_dt.isoformat() + 'Z',
        timeMax=end_dt.isoformat() + 'Z',
        maxResults=50,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    # 시간 필터링
    if time_filter:
        def in_range(event):
            dt_raw = event['start'].get('dateTime')
            if not dt_raw:
                return False
            dt = datetime.datetime.fromisoformat(dt_raw.replace('Z', '+00:00'))
            hour = dt.hour
            if time_filter == "morning":
                return 6 <= hour < 12
            if time_filter == "afternoon":
                return 12 <= hour < 18
            if time_filter == "evening":
                return 18 <= hour <= 23
            if time_filter == "lunch":
                return 11 <= hour < 14
            return True
        events = list(filter(in_range, events))

    # 키워드 필터링
    if keyword and isinstance(keyword, str):
        events = [e for e in events if keyword.lower() in e.get('summary', '').lower()]

    return events

def format_event_list(events):
    weekday_ko = ["월", "화", "수", "목", "금", "토", "일"]
    result = []
    for e in events:
        start_raw = e['start'].get('dateTime', e['start'].get('date'))
        end_raw = e['end'].get('dateTime', e['end'].get('date'))

        try:
            start_dt = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
            end_dt = datetime.datetime.fromisoformat(end_raw.replace('Z', '+00:00'))
            duration = end_dt - start_dt
            duration_hours = round(duration.total_seconds() / 3600, 1)

            dow = weekday_ko[start_dt.weekday()]
            date_str = start_dt.strftime(f"%y/%m/%d({dow}) %H:%M")
            end_str = end_dt.strftime("%H:%M")
            display = f"{date_str}~{end_str} ({duration_hours}h) - {e.get('summary', '제목 없음')}"
        except:
            display = f"{start_raw} - {e.get('summary', '제목 없음')}"

        result.append(f"🗓 {display}")
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

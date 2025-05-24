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


def get_events_for_dates(dates, time_filter=None, keyword_filter=None):
    service = get_calendar_service()
    all_events = []
    seen = set()

    for date_str in dates:
        date_obj = datetime.date.fromisoformat(date_str)
        start_dt = datetime.datetime.combine(date_obj, datetime.time.min)
        end_dt = datetime.datetime.combine(date_obj, datetime.time.max)
        start = start_dt.isoformat() + 'Z'
        end = end_dt.isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start,
            timeMax=end,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        items = events_result.get('items', [])

        filtered = []
        for e in items:
            dt_raw = e['start'].get('dateTime')
            if dt_raw:
                dt = datetime.datetime.fromisoformat(dt_raw.replace('Z', '+00:00'))
                hour = dt.hour
                if time_filter == "lunch" and not (11 <= hour < 14):
                    continue
                if time_filter == "evening" and not (18 <= hour < 21):
                    continue
            if keyword_filter and keyword_filter.lower() not in e.get('summary', '').lower():
                continue

            key = (e.get('summary'), e['start'].get('dateTime'))
            if key in seen:
                continue
            seen.add(key)

            e['__date'] = dt.date().isoformat() if dt_raw else date_str
            filtered.append(e)

        all_events.extend(filtered)
    return all_events


def summarize_events_compact(dates, events):
    weekday_ko = ["월", "화", "수", "목", "금", "토", "일"]
    if not events:
        return "📅 해당 날짜들에는 일정이 없습니다."

    result = []
    by_date = {d: [] for d in dates}
    for e in events:
        by_date[e['__date']].append(e)

    for d in dates:
        if not by_date[d]:
            continue
        date_obj = datetime.date.fromisoformat(d)
        dow = weekday_ko[date_obj.weekday()]
        header = f"📅 {d[5:]}({dow})"
        rows = []
        for e in by_date[d]:
            start = e['start'].get('dateTime', e['start'].get('date'))
            end = e['end'].get('dateTime', e['end'].get('date'))
            summary = e.get('summary', '제목 없음')
            try:
                start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
                duration_raw = (end_dt - start_dt).total_seconds() / 3600
                duration = int(duration_raw) if duration_raw.is_integer() else round(duration_raw, 1)
                rows.append(f"- {start_dt.strftime('%H:%M')}~{end_dt.strftime('%H:%M')} ({duration}h): {summary}")
            except:
                rows.append(f"- {summary}")
        result.append(header + "\n" + "\n".join(rows))

    return "\n\n".join(result)


def summarize_available_days(dates, time_filter):
    weekday_ko = ["월", "화", "수", "목", "금", "토", "일"]
    events = get_events_for_dates(dates, time_filter=time_filter)
    busy_dates = {e['__date'] for e in events}
    available = [d for d in dates if d not in busy_dates]
    if not available:
        return "📅 요청하신 조건에 한가한 날이 없습니다."
    rows = []
    for d in available:
        date_obj = datetime.date.fromisoformat(d)
        dow = weekday_ko[date_obj.weekday()]
        rows.append(f"- {d[5:]}({dow})")
    return "🗓 한가한 날:\n" + "\n".join(rows)

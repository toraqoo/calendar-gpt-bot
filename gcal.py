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


def get_events_for_dates(dates):
    service = get_calendar_service()
    all_events = []
    for date_str in dates:
        date_obj = datetime.date.fromisoformat(date_str)
        start = datetime.datetime.combine(date_obj, datetime.time.min).isoformat() + 'Z'
        end = datetime.datetime.combine(date_obj, datetime.time.max).isoformat() + 'Z'
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start,
            timeMax=end,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        items = events_result.get('items', [])
        for e in items:
            e['__date'] = date_str  # 일정의 기준 날짜 기록
        all_events.extend(items)
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
                duration = round((end_dt - start_dt).total_seconds() / 3600, 1)
                rows.append(f"- {start_dt.strftime('%H:%M')}~{end_dt.strftime('%H:%M')} ({duration}h): {summary}")
            except:
                rows.append(f"- {summary}")
        result.append(header + "\n" + "\n".join(rows))

    return "\n\n".join(result)

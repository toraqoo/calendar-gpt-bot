# main.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from date_parser import extract_dates_from_text
from gcal import get_events, filter_events, find_available_days, format_event_list, format_available_days

app = FastAPI()

class RequestModel(BaseModel):
    user_input: str

@app.get("/")
def root():
    return {"message": "Calendar Bot is running!"}

@app.post("/calendar")
def calendar_handler(request: RequestModel):
    user_input = request.user_input
    parsed = extract_dates_from_text(user_input)
    dates = parsed['dates']
    time_filter = parsed['time_filter']
    keyword_filter = parsed['keyword_filter']
    find_available = parsed['find_available']

    if not dates:
        return "❗ 날짜를 인식하지 못했어요. 예: '5/26', '다음주 월', '6월 전체'"

    events = get_events(dates)

    if find_available:
        available_days = find_available_days(events, dates, time_filter=time_filter)
        if not available_days:
            return "❌ 요청한 조건에 맞는 '한가한 날'이 없습니다."
        return format_available_days(available_days)

    filtered_events = filter_events(events, time_filter=time_filter, keyword_filter=keyword_filter)
    if not filtered_events:
        return "❌ 해당 조건에 맞는 일정이 없습니다."
    return format_event_list(filtered_events)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("📨 텔레그램 메시지 수신:", data)
    # TODO: 메시지 파싱 및 응답 로직 연결
    return {"ok": True}

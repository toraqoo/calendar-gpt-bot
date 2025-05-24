from fastapi import FastAPI, Request
import os
import httpx
from gcal import get_events_for_dates, summarize_events_compact, summarize_available_days
from date_parser import extract_dates_from_text

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 v11 - 한가, 키워드, 평일 포함"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다! 예: 6월 전체 골프, 다음주 점심 한가, 다담주 월화수, 다음주 평일 저녁")
        return {"ok": True}

    try:
        dates, time_filter, keyword_filter, available_only, weekday_filter = extract_dates_from_text(user_text)
        if not dates:
            await send(chat_id, "❗ 날짜를 인식하지 못했어요. 예: '5/26', '다음주 월', '6월 전체'")
            return {"ok": True}

        if available_only:
            result = summarize_available_days(dates, time_filter)
        else:
            events = get_events_for_dates(dates, time_filter=time_filter, keyword_filter=keyword_filter)
            result = summarize_events_compact(dates, events)

        await send(chat_id, result)

    except Exception as e:
        await send(chat_id, f"[오류] {str(e)}")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

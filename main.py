from fastapi import FastAPI, Request
import os
import httpx
from gcal import get_events_for_dates, summarize_events_compact
from date_parser import extract_dates_from_text

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 v10 - 날짜 파싱 고정형"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다! 다음과 같이 질문해보세요:\n- 5/26 일정은?\n- 다음주 월화수 일정은?\n- 이번주 월, 화 일정 알려줘\n- 담주 저녁 약속 알려줘")
        return {"ok": True}

    try:
        dates, time_filter = extract_dates_from_text(user_text)
        if not dates:
            await send(chat_id, "❗ 날짜를 인식하지 못했어요. 예: '5/26', '다음주 월', '이번주 월화수'")
            return {"ok": True}

        events = get_events_for_dates(dates, time_filter=time_filter)
        summary = summarize_events_compact(dates, events)
        await send(chat_id, summary)

    except Exception as e:
        await send(chat_id, f"[오류] {str(e)}")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

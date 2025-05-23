from fastapi import FastAPI, Request
import os
import httpx
import datetime
from openai import OpenAI
from gcal import get_today_events, get_tomorrow_events, get_nextweek_evening_free_days

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 최신 버전 동작 중 ✅"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    # 명령 분석
    user_text_lower = user_text.lower()

    if user_text.startswith("/start"):
        await send(chat_id, "Mk님의 일정 비서에 오신 걸 환영합니다! 아래처럼 말해보세요:\n\n- 오늘 일정\n- 내일 약속 있어?\n- 다음주에 저녁 시간 되는 날은?")
        return {"ok": True}

    if "오늘" in user_text and "일정" in user_text:
        events = get_today_events()
        if not events:
            await send(chat_id, "📅 오늘은 일정이 없습니다.")
        else:
            msg = "📅 오늘 일정:\n" + "\n".join(
                f"• {e['start'].get('dateTime', e['start'].get('date'))} - {e.get('summary', '제목 없음')}"
                for e in events
            )
            await send(chat_id, msg)
        return {"ok": True}

    if "내일" in user_text:
        events = get_tomorrow_events()
        if not events:
            await send(chat_id, "📅 내일은 일정이 없습니다.")
        else:
            msg = "📅 내일 일정:\n" + "\n".join(
                f"• {e['start'].get('dateTime', e['start'].get('date'))} - {e.get('summary', '제목 없음')}"
                for e in events
            )
            await send(chat_id, msg)
        return {"ok": True}

    if "다음주" in user_text and ("비는 날" in user_text or "약속 없는" in user_text or "저녁" in user_text):
        free_days = get_nextweek_evening_free_days()
        if free_days:
            await send(chat_id, "🍽 다음주 저녁 약속 없는 날:\n" + "\n".join(free_days))
        else:
            await send(chat_id, "❗ 다음주엔 매일 저녁 약속이 있습니다.")
        return {"ok": True}

    # GPT fallback
    gpt_response = await ask_gpt(user_text)
    await send(chat_id, gpt_response)
    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt(text):
    try:
        res = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 텔레그램 일정 비서야. 구글 캘린더와 연결돼있고, 일정 조회와 설명을 자연스럽게 해줘."},
                {"role": "user", "content": text}
            ]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"[GPT 오류] {e}"

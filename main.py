from fastapi import FastAPI, Request
import os
import httpx
import datetime
from openai import OpenAI
from gcal import get_today_events, get_events_by_filter, format_event_list
import json

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 - 자연어 버전"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서에 오신 걸 환영합니다!\n\n예시:\n- 오늘 일정 뭐 있어?\n- 다음주 월요일 일정 보여줘\n- 6월에 골프 약속 몇 개 있어?")
        return {"ok": True}

    # 1. GPT에게 intent 분석 요청
    try:
        parsed = await ask_gpt_intent(user_text)
    except Exception as e:
        await send(chat_id, f"[GPT Intent 분석 오류] {str(e)}")
        return {"ok": True}

    # 2. 캘린더 API 호출
    if parsed.get("action") == "get_schedule":
        try:
            events = get_events_by_filter(parsed)
            if not events:
                await send(chat_id, "📅 일정이 없습니다.")
            else:
                await send(chat_id, format_event_list(events))
        except Exception as e:
            await send(chat_id, f"[일정 불러오기 오류] {str(e)}")
    else:
        await send(chat_id, f"❓ '{parsed.get('action')}' 요청은 아직 구현되지 않았습니다.")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt_intent(text):
    system_prompt = (
        "너는 사용자의 일정 관련 요청을 구조화된 JSON으로 반환해야 해.\n"
        "모든 날짜는 반드시 yyyy-mm-dd 형식으로 반환해.\n"
        "time_filter는 'morning', 'afternoon', 'evening', 'lunch' 중 선택.\n"
        "예시 응답:\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-06-03\", \"end\": \"2025-06-05\"},\n"
        "  \"time_filter\": \"lunch\",\n"
        "  \"keyword_filter\": \"골프\"\n"
        "}"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )

    content = response.choices[0].message.content
    return json.loads(content)

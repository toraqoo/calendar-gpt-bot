from fastapi import FastAPI, Request
import os
import httpx
import datetime
from openai import OpenAI
from gcal import get_today_events, get_events_by_filter
import json

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 GPT-Intent 버전 ✅"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk님의 일정 비서입니다!\n말로 물어보세요:\n예: 다음주 일정 보여줘, 5월 27일 일정 알려줘, 골프 약속 몇개 있어")
        return {"ok": True}

    # 1단계: GPT에게 intent JSON 요청
    try:
        parsed = await ask_gpt_intent(user_text)
    except Exception as e:
        await send(chat_id, f"[GPT Intent 분석 오류] {str(e)}")
        return {"ok": True}

    if parsed.get("action") == "get_schedule":
        try:
            events = get_events_by_filter(parsed)
            if not events:
                await send(chat_id, "📅 해당 조건에 맞는 일정이 없습니다.")
            else:
                msg = "📅 일정:\n" + "\n".join([
                    f"• {e['start'].get('dateTime', e['start'].get('date'))} - {e.get('summary', '제목 없음')}"
                    for e in events
                ])
                await send(chat_id, msg)
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
        "너는 일정 비서야. 사용자의 자연어 요청을 보고 JSON 형식으로 intent를 추출해야 해.\n"
        "아래와 같은 형식으로 응답해줘:\n\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\n"
        "    \"start\": \"2025-05-27\",\n"
        "    \"end\": \"2025-05-31\"\n"
        "  },\n"
        "  \"time_filter\": \"evening\", \n"
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

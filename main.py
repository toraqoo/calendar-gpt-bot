from fastapi import FastAPI, Request
import os
import httpx
import datetime
from openai import OpenAI
from gcal import get_events_by_filter
import json

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 v3 - 자연어 → 캘린더 → 요약"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다. 자연어로 질문하세요:\n\n예: 다음주 월요일 일정은?\n6월 골프 약속은?\n이번주 저녁 약속은?")
        return {"ok": True}

    try:
        intent = await ask_gpt_intent(user_text)
        events = get_events_by_filter(intent)
        response = await summarize_events_with_gpt(user_text, events)
        await send(chat_id, response)
    except Exception as e:
        await send(chat_id, f"[오류] {str(e)}")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt_intent(question):
    system_prompt = (
        "너는 일정 비서야. 사용자의 질문을 보고 다음과 같은 JSON 구조로 반환해야 해.\n"
        "모든 날짜는 반드시 ISO yyyy-mm-dd 형식으로 반환해야 해. '다음주 월요일', '6월 전체' 등의 표현도 정확한 날짜로 변환해서 반환해.\n"
        "예시:\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-06-03\", \"end\": \"2025-06-03\"},\n"
        "  \"time_filter\": \"lunch\",  // 생략 가능\n"
        "  \"keyword_filter\": \"골프\"  // 생략 가능\n"
        "}"
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    )
    content = response.choices[0].message.content.strip()
    print("[GPT INTENT 응답]:\n", content)

    try:
        return json.loads(content)
    except Exception as e:
        raise ValueError(f"GPT 응답을 JSON으로 파싱하지 못했습니다:\n{content}")

async def summarize_events_with_gpt(question, events):
    if not events:
        return "📅 요청하신 조건에 맞는 일정이 없습니다."

    blocks = []
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        end = e['end'].get('dateTime', e['end'].get('date'))
        summary = e.get('summary', '제목 없음')
        try:
            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration = round((end_dt - start_dt).total_seconds() / 3600, 1)
            dow = ["월", "화", "수", "목", "금", "토", "일"][start_dt.weekday()]
            blocks.append(f"🗓 {start_dt.strftime(f'%y/%m/%d({dow}) %H:%M')}~{end_dt.strftime('%H:%M')} ({duration}h): {summary}")
        except:
            blocks.append(f"• {summary}")

    return f"{question.strip()}에 대한 일정입니다:\n" + "\n".join(blocks)

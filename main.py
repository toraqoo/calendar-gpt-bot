from fastapi import FastAPI, Request
import os
import httpx
import datetime
from openai import OpenAI
from gcal import get_events_by_filter, format_event_list
import json

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 v3 - 자연어 → 실행 → 요약"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서에 오신 걸 환영합니다!\n자연어로 질문하세요:\n\n- 다음주 월요일 일정은?\n- 6월 골프 약속은?\n- 다음주 저녁 약속 없는 날은?")
        return {"ok": True}

    try:
        # 1. GPT로 intent 추출
        intent = await ask_gpt_intent(user_text)

        # 2. Google Calendar 일정 조회
        events = get_events_by_filter(intent)

        # 3. 결과를 다시 GPT에게 넘겨서 자연어 요약
        final_answer = await summarize_events_with_gpt(user_text, events)

        await send(chat_id, final_answer)
    except Exception as e:
        await send(chat_id, f"[오류] {str(e)}")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt_intent(question):
    system_prompt = (
        "너는 일정 비서야. 사용자의 자연어 질문을 보고 JSON 형식으로 일정을 요청해야 해.\n"
        "모든 날짜는 yyyy-mm-dd 형식으로 반환해야 하며, 예시는 다음과 같아:\n\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-06-03\", \"end\": \"2025-06-03\"},\n"
        "  \"time_filter\": \"lunch\",\n"
        "  \"keyword_filter\": \"골프\"\n"
        "}"
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
    )
    return json.loads(response.choices[0].message.content)

async def summarize_events_with_gpt(question, events):
    events_text = format_event_list(events)
    prompt = (
        "사용자가 아래와 같은 일정 요청을 했어:\n"
        f"{question}\n\n"
        "그리고 일정 데이터는 다음과 같아:\n"
        f"{events_text}\n\n"
        "이 데이터를 바탕으로, 친절하고 자연스러운 말투로 요약해서 설명해줘."
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "너는 일정 비서야. 데이터 기반으로 깔끔하게 말해줘."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

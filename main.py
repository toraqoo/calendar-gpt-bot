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
    return {"message": "Mk 일정 비서 v3 - 자연어 → 실행 → 자연어 응답"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다. 그냥 말로 물어보세요:\n- 다음주 화요일 일정은?\n- 다음주 저녁에 한가한 날은?\n- 6월 골프 약속 뭐 있어?")
        return {"ok": True}

    try:
        # 1. GPT → intent JSON
        intent = await ask_gpt_intent(user_text)

        # 2. 서버 → 일정 조회
        events = get_events_by_filter(intent)

        # 3. GPT → 응답 요약
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
        "너는 일정 비서야. 사용자의 자연어 요청을 보고 JSON으로 일정 요청을 만들어줘.\n"
        "반드시 날짜는 yyyy-mm-dd 형식으로 반환해.\n"
        "예시 응답:\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-05-27\", \"end\": \"2025-05-27\"},\n"
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
    content = response.choices[0].message.content.strip()

    # 디버깅 로그 (Render 콘솔에서 확인 가능)
    print("[GPT INTENT 응답]:\n", content)

    try:
        return json.loads(content)
    except Exception as e:
        raise ValueError(f"GPT 응답을 JSON으로 해석하지 못했습니다:\n{content}")

async def summarize_events_with_gpt(question, events):
    if not events:
        return "📅 요청하신 조건에 해당하는 일정이 없습니다."

    events_text = format_event_list(events)
    prompt = (
        "사용자가 다음과 같은 질문을 했어:\n"
        f"{question}\n\n"
        "그리고 일정 데이터는 다음과 같아:\n"
        f"{events_text}\n\n"
        "이걸 바탕으로 자연스럽고 친절하게 요약해서 설명해줘. 단정하고 한글로 깔끔하게 써줘."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "너는 일정 비서야. 데이터를 바탕으로 자연스럽게 설명해줘."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

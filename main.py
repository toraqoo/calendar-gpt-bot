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
    return {"message": "Mk 일정 비서 v4 - GPT가 질문 해석부터 응답까지 처리"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다! 자연스럽게 물어보세요.\n\n예: 다음주 수요일에 회의 있어?\n6월 전체 일정 알려줘\n다다음주 월요일 저녁 일정 뭐 있어?")
        return {"ok": True}

    try:
        # 1. GPT에게 질문 해석 요청
        intent = await ask_gpt_intent(user_text)

        # 2. intent 기반으로 일정 조회
        events = get_events_by_filter(intent)

        # 3. 일정 데이터를 기반으로 GPT에게 요약 요청
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
        "너는 일정 비서야. 사용자의 자연어 질문을 보고 반드시 정확한 intent JSON으로 반환해야 해.\n"
        "모든 날짜는 반드시 yyyy-mm-dd 형식으로 변환해. '다음주 화요일', '5/27(화)', '6월 전체' 등의 표현도 계산해서 명확한 날짜 범위로 바꿔줘야 해.\n\n"
        "반환 예시:\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-05-27\", \"end\": \"2025-05-27\"},\n"
        "  \"time_filter\": \"evening\",  // optional\n"
        "  \"keyword_filter\": \"회의\"    // optional\n"
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
        raise ValueError(f"GPT 응답을 JSON으로 해석할 수 없습니다:\n{content}")

async def summarize_events_with_gpt(question, events):
    if not events:
        return "📅 요청하신 조건에 해당하는 일정이 없습니다."

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
            blocks.append(f"- {start_dt.strftime(f'%H:%M')}~{end_dt.strftime('%H:%M')} ({duration}h): {summary}")
        except:
            blocks.append(f"- {summary}")

    date_str = start_dt.strftime("%m/%d") + f"({dow})"
    prompt = f"사용자가 '{question}'라고 물었고, {date_str} 일정은 다음과 같아:\n" + "\n".join(blocks) + "\n간결하게 정리해서 말해줘."

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "너는 일정 비서야. 사용자 질문에 대한 일정을 예쁘고 간단하게 정리해줘."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

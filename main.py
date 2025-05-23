from fastapi import FastAPI, Request
import os
import httpx
import datetime
from openai import OpenAI
from gcal import get_events_by_filter
import json
import re

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Mk 일정 비서 v9 - GPT 해석 실패 보완"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다. 자연어로 일정 질문을 해보세요. 예: \n- 5/27 일정은?\n- 다음주 수요일에 뭐 있어?\n- 6월 골프 약속은?")
        return {"ok": True}

    try:
        intent = await ask_gpt_intent(user_text)
        start = intent.get("date_range", {}).get("start")
        end = intent.get("date_range", {}).get("end")

        if not start or not re.match(r"\\d{4}-\\d{2}-\\d{2}", start):
            raise ValueError("GPT가 반환한 날짜가 유효하지 않습니다.")

        events = get_events_by_filter(intent)

        if intent.get("weekly_summary"):
            response = await summarize_weekly_with_gpt(user_text, events)
        else:
            response = await summarize_events_with_gpt(user_text, events)

        await send(chat_id, response)

    except Exception as e:
        today = datetime.date.today().isoformat()
        fallback_intent = {
            "action": "get_schedule",
            "date_range": {"start": today, "end": today},
            "time_filter": None,
            "keyword_filter": None,
            "weekly_summary": False
        }
        try:
            events = get_events_by_filter(fallback_intent)
            fallback_response = await summarize_events_with_gpt("오늘 일정", events)
            await send(chat_id, fallback_response)
        except:
            await send(chat_id, f"[오류] {str(e)}")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt_intent(question):
    prompt = (
        "너는 일정 비서야. 사용자의 자연어 요청을 보고 다음 JSON 형식으로 intent를 반환해:",
        "\n{",
        "\"action\": \"get_schedule\",",
        "\"date_range\": {\"start\": \"yyyy-mm-dd\", \"end\": \"yyyy-mm-dd\"},",
        "\"time_filter\": \"lunch\",",
        "\"keyword_filter\": \"골프\",",
        "\"weekly_summary\": true",
        "}",
        "❗ 반드시 날짜 표현은 ISO 포맷으로 변환해야 해. 예: '다음주 월요일' → '2025-06-03'"
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "\n".join(prompt)},
            {"role": "user", "content": question}
        ]
    )
    return json.loads(response.choices[0].message.content.strip())

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
            blocks.append(f"- {start_dt.strftime('%H:%M')}~{end_dt.strftime('%H:%M')} ({duration}h): {summary} ({start_dt.strftime('%y/%m/%d')}({dow}))")
        except:
            blocks.append(f"- {summary}")

    prompt = f"사용자 질문: {question}\n일정:\n" + "\n".join(blocks) + "\n정리해서 간단히 말해줘."

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "일정을 간결하게 요약해서 말해줘."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

async def summarize_weekly_with_gpt(question, events):
    if not events:
        return "📅 요청하신 조건에 해당하는 일정이 없습니다."

    weekly = {}
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        try:
            dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            year, week, _ = dt.isocalendar()
            key = f"{year}-W{week}"
            weekly.setdefault(key, []).append(e)
        except:
            continue

    summaries = []
    for week_key, week_events in weekly.items():
        blocks = []
        for e in week_events:
            try:
                s = e['start']['dateTime']
                e_dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
                time_str = e_dt.strftime('%m/%d(%a) %H:%M')
                blocks.append(f"- {time_str}: {e.get('summary', '제목 없음')}")
            except:
                blocks.append(f"- {e.get('summary', '제목 없음')}")
        summaries.append(f"📆 {week_key} 주차 일정\n" + "\n".join(blocks))

    return "\n\n".join(summaries)

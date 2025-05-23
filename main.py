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
    return {"message": "Mk 일정 비서 v7 - GPT 해석 + fallback 완비"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다!\n그냥 말해주세요:\n- 담주 화요일 일정은?\n- 6월 저녁 약속 주차별로 알려줘\n- 5/27 뭐 있어?")
        return {"ok": True}

    try:
        # 1. GPT intent 요청
        intent = await ask_gpt_intent(user_text)
        events = get_events_by_filter(intent)
        if intent.get("weekly_summary"):
            response = await summarize_weekly_with_gpt(user_text, events)
        else:
            response = await summarize_events_with_gpt(user_text, events)
        await send(chat_id, response)

    except Exception as e:
        await send(chat_id, f"[오류] {str(e)}")

    return {"ok": True}

async def send(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt_intent(question):
    base_prompt = (
        "너는 일정 비서야. 사용자의 자연어 요청을 JSON intent 형식으로 분석해줘.\n"
        "모든 날짜는 반드시 yyyy-mm-dd 형식으로 변환해. 예: '다음주 월' → '2025-06-03'\n"
        "표현 예시:\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-06-03\", \"end\": \"2025-06-03\"},\n"
        "  \"time_filter\": \"lunch\",\n"
        "  \"keyword_filter\": \"회의\",\n"
        "  \"weekly_summary\": false\n"
        "}"
    )

    messages = [
        {"role": "system", "content": base_prompt},
        {"role": "user", "content": question}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)

    except Exception:
        # fallback: GPT 재질문 시도
        try:
            retry_prompt = f"앞서 너는 다음 질문에 대해 JSON intent 형식으로 응답하지 못했어:\n\n'{question}'\n다시 명확한 JSON intent로만 응답해줘. 날짜는 yyyy-mm-dd 형식 필수."
            retry_messages = [
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": retry_prompt}
            ]
            response2 = client.chat.completions.create(
                model="gpt-4",
                messages=retry_messages
            )
            content2 = response2.choices[0].message.content.strip()
            return json.loads(content2)
        except Exception as fallback_e:
            # 최후 fallback
            today = datetime.date.today().isoformat()
            return {
                "action": "get_schedule",
                "date_range": {"start": today, "end": today},
                "time_filter": None,
                "keyword_filter": None,
                "weekly_summary": False
            }

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

    prompt = f"사용자가 '{question}'라고 물었고, 일정은 아래와 같아:\n" + "\n".join(blocks) + "\n간결하게 정리해서 대답해줘."

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "너는 일정 비서야. 친절하고 간결하게 요약해서 말해줘."},
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

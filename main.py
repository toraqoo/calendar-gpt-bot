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
    return {"message": "Mk 일정 비서 v8 - GPT 강화 + fallback 확정"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다! 아래처럼 질문해보세요:\n\n- 담주 월요일 일정은?\n- 5/26~5/29 일정 보여줘\n- 6월 저녁 약속 주차별로 정리해줘")
        return {"ok": True}

    try:
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
        "너는 일정 비서야. 사용자의 자연어 질문을 다음 JSON 형식으로 분석해야 해:\n\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"yyyy-mm-dd\", \"end\": \"yyyy-mm-dd\"},\n"
        "  \"time_filter\": \"morning|afternoon|evening|lunch\",\n"
        "  \"keyword_filter\": \"골프\",\n"
        "  \"weekly_summary\": true|false\n"
        "}\n\n"
        "❗ 반드시 모든 날짜 표현은 ISO yyyy-mm-dd 형식으로 변환해서 반환해.\n"
        "❗ '다음주 월', '5/26(월)', '6월 전체' 등의 표현도 너가 직접 계산해서 날짜로 넣어야 해.\n"
        "❗ 쉼표로 여러 날짜가 있을 경우 → 최소~최대 날짜 범위로 묶어서 반환해."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": question}
            ]
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except:
        # 재질문
        try:
            retry = f"이전 질문에 대해 JSON intent를 제대로 못 만들었어. 아래 질문을 보고 JSON intent로 다시 반환해:\n'{question}'"
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": base_prompt},
                    {"role": "user", "content": retry}
                ]
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except:
            # fallback
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

    prompt = (
        f"사용자 질문: {question}\n\n"
        "일정:\n" + "\n".join(blocks) +
        "\n위 내용을 한글로 간결하고 자연스럽게 정리해서 알려줘. 날짜 요일은 그대로 유지해."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "너는 일정 비서야. 데이터를 깔끔하게 정리해서 자연스럽게 대답해줘."},
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

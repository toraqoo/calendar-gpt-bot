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
    return {"message": "Mk 일정 비서 v6 - 자연어 → intent + 요약 + 주차 그룹"}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send(chat_id, "Mk 일정 비서입니다. 자연스럽게 물어보세요.\n예:\n- 다음주 월요일 일정은?\n- 5월 전체 일정은?\n- 6월 저녁 약속 주차별로 정리해줘")
        return {"ok": True}

    try:
        # 1. GPT가 intent JSON 생성
        intent = await ask_gpt_intent(user_text)

        # 2. 일정 조회
        events = get_events_by_filter(intent)

        # 3. 주차별 요약 여부 확인
        weekly_summary = intent.get("weekly_summary", False)
        if weekly_summary:
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
    system_prompt = (
        "너는 일정 비서야. 사용자의 질문을 아래 JSON 형식으로 intent로 추출해줘.\n"
        "모든 날짜 표현은 반드시 yyyy-mm-dd 형식으로 변환해야 해. '다음주 월', '5월 전체', '6/1~6/7' 같은 표현도 정확한 날짜 범위로 바꿔줘.\n"
        "만약 사용자가 '주차별 요약해줘'라고 말하면 weekly_summary: true로 추가해.\n\n"
        "예시 응답:\n"
        "{\n"
        "  \"action\": \"get_schedule\",\n"
        "  \"date_range\": {\"start\": \"2025-06-01\", \"end\": \"2025-06-30\"},\n"
        "  \"time_filter\": \"evening\",\n"
        "  \"keyword_filter\": \"골프\",\n"
        "  \"weekly_summary\": true\n"
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
            blocks.append(f"- {start_dt.strftime(f'%H:%M')}~{end_dt.strftime('%H:%M')} ({duration}h): {summary} ({start_dt.strftime('%y/%m/%d')}({dow}))")
        except:
            blocks.append(f"- {summary}")

    prompt = (
        f"사용자 질문: {question}\n\n"
        "일정 목록:\n" + "\n".join(blocks) +
        "\n\n일정을 간결하게 정리해서 대답해줘. 포맷은 '시간~시간 (x.xh): 제목 (날짜)' 형식."
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

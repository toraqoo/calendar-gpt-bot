from fastapi import FastAPI, Request
import os
import httpx
import openai
from gcal import get_today_events

app = FastAPI()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

openai.api_key = OPENAI_API_KEY

@app.get("/")
def root():
    return {"message": "Mk님의 일정 비서 서버 작동 중입니다."}

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    user_text = data.get("message", {}).get("text", "")

    if not chat_id or not user_text:
        return {"ok": False}

    if user_text.startswith("/start"):
        await send_message(chat_id, "Mk님의 일정 비서에 오신 걸 환영합니다!\n자연어로 물어보세요:\n- 오늘 일정 뭐 있어?\n- 다음주 수요일에 회식 잡아줘")
        return {"ok": True}

    # ✅ 1. 특정 키워드 매칭 → 오늘 일정 조회
    if "오늘" in user_text and "일정" in user_text:
        events = get_today_events()
        if not events:
            reply = "📅 오늘은 등록된 일정이 없습니다."
        else:
            reply = "📅 오늘 일정:\n" + "\n".join([
                f"🕒 {e['start'].get('dateTime', e['start'].get('date'))} - {e.get('summary', '제목 없음')}"
                for e in events
            ])
        await send_message(chat_id, reply)
        return {"ok": True}

    # ✅ 2. 그 외는 GPT로 전달
    gpt_reply = await ask_gpt(user_text)
    await send_message(chat_id, gpt_reply)
    return {"ok": True}

async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )

async def ask_gpt(user_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 텔레그램 일정 비서야. 구글 캘린더에서 일정을 직접 조회하거나 등록할 수 있어. 사용자의 일상적인 질문에 자연스럽게 답해줘."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"[GPT 오류] {str(e)}"

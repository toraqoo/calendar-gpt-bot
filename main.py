from fastapi import FastAPI, Request
import os
import httpx

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@app.get("/")
def root():
    return {"message": "Mk님의 일정 비서 작동 중"}

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '')

    if text == "/start":
        await send_message(chat_id, "Mk님의 일정 비서에 오신 걸 환영합니다!\n\n예시 명령:\n- /오늘일정\n- 이번주에 저녁 약속은?\n- 다음주 수요일 6시에 회식 잡아줘")

    elif text == "/오늘일정":
        await send_message(chat_id, "📅 오늘 일정은 준비 중입니다!")  # 향후 GPT + 캘린더 연동 예정

    else:
        await send_message(chat_id, f"❓ '{text}'에 대해 아직 학습되지 않았어요!")

    return {"ok": True}

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

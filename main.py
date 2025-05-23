from fastapi import FastAPI, Request
import os
import httpx
import openai

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
        await send_message(chat_id, "Mk님의 일정 비서에 오신 걸 환영합니다!\n자연어로 물어보세요:\n- 내일 약속 있어?\n- 다음주 회식 잡아줘")
        return {"ok": True}

    # GPT 응답 호출
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
                {"role": "system", "content": "너는 텔레그램 일정 비서야. 사용자의 자연어 일정 요청에 대해 부드럽고 간결하게 응답해줘. 실제 캘린더 연동은 아직 없어. 예시를 들어줘."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"[GPT 오류] {str(e)}"

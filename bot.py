import os
import httpx
import openai

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

openai.api_key = OPENAI_API_KEY

async def handle_telegram_update(data):
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_text = message.get("text", "")

    if not chat_id or not user_text:
        return

    if user_text.startswith("/start"):
        await send_message(chat_id, "Mk님의 일정 비서에 오신 걸 환영합니다!\n\n예시:\n- 내일 일정 있어?\n- 다음주 수요일 회식 잡아줘\n- 이번 주 바쁜 날은?")
        return

    # ✅ GPT에 질문 보내기
    gpt_response = await ask_gpt(user_text)
    await send_message(chat_id, gpt_response)

async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt(user_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "너는 사용자의 일정 요청을 받아서 자연스럽게 응답해주는 일정 비서야. 구글 캘린더 연동은 아직 안 되어 있으니, 예시로 일정처럼 말해줘."},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"GPT 처리 중 오류가 발생했습니다: {str(e)}"

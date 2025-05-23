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
        await send_message(chat_id, "Mk님의 일정 비서에 오신 걸 환영합니다!\n\n예시 명령:\n- /오늘일정\n- 이번주에 저녁 약속은?\n- 다음주 수요일 6시에 회식 잡아줘")
        return

    # 👇 GPT에게 질문을 보내고, 자연어 분석 결과 받아오기
    gpt_response = await ask_gpt(user_text)

    # 📩 결과 전송
    await send_message(chat_id, gpt_response)

async def send_message(chat_id, text):
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

async def ask_gpt(user_text):
    system_prompt = (
        "너는 텔레그램 일정 비서야. 사용자가 구글 캘린더에서 일정 확인하거나 추가하려고 말해. "
        "사용자의 말을 이해해서 자연스럽게 응답해줘. 일정을 실제로 등록하거나 조회하지 말고, 대신 예시로 알려줘."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7
        )
        return response.choices[0].message["content"]

    except Exception as e:
        return f"GPT 처리 중 오류가 발생했습니다: {str(e)}"

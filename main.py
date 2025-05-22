from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Mk님의 일정 비서 서버 작동 중!"}
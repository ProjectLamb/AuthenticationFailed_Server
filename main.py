# main.py
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json

# 환경변수 로드가 가장 먼저 실행되어야 합니다.
load_dotenv()
if not (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
    raise ValueError("⚠️ .env 파일에 API 키가 없습니다!")

from services import ai_service

app = FastAPI(title="AI 파트너 API", version="1.0.0")


class ChatRequest(BaseModel):
    message: str
    minigame_type: str = "스마트폰 본인 인증"
    target_code: str = ""


@app.post("/api/v1/chat", tags=["1. AI Partner (Text)"])
async def talk_to_partner_text(req: ChatRequest):
    try:
        # 비즈니스 로직(서비스) 호출
        ai_reply = await ai_service.generate_text_reply(req.message, req.minigame_type, req.target_code)

        # [핵심] 이메지네이션 패닉은 유니티에서 바로 읽을 수 있게 순수 JSON을 던져줘야 함
        if req.minigame_type == "이메지네이션 패닉":
            cleaned_json = ai_reply.replace("```json", "").replace("```", "").strip()
            return JSONResponse(content=json.loads(cleaned_json))

        # 일반 미니게임은 기존 포맷 유지
        is_cleared = req.target_code in ai_reply if req.target_code else False
        return {"reply": ai_reply, "is_cleared": is_cleared}

    except Exception as e:
        return {"reply": f"서버 터짐. 로그 확인해봐. ({str(e)})", "is_cleared": False}


@app.post("/api/v1/voice-chat", tags=["2. AI Partner (Voice)"])
async def talk_to_partner_voice(
        background_tasks: BackgroundTasks,
        audio_file: UploadFile = File(...),
        minigame_type: str = Form("스마트폰 본인 인증"),
        target_code: str = Form("")
):
    user_audio_path = f"temp_user_{uuid.uuid4()}.wav"
    with open(user_audio_path, "wb") as buffer:
        buffer.write(await audio_file.read())

    try:
        # 서비스 호출해서 음성 파일 경로 받아오기
        ai_audio_path = await ai_service.generate_voice_reply(user_audio_path, minigame_type, target_code)

        os.remove(user_audio_path)
        background_tasks.add_task(os.remove, ai_audio_path)

        return FileResponse(path=ai_audio_path, media_type="audio/mpeg", filename="ai_reply.mp3")
    except Exception as e:
        if os.path.exists(user_audio_path): os.remove(user_audio_path)
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
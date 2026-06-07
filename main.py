# main.py
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
import uuid

# 환경변수 로드가 가장 먼저 실행되어야 합니다.
load_dotenv()
if not (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
    raise ValueError("⚠️ .env 파일에 API 키가 없습니다!")

from services import ai_service

app = FastAPI(title="AI 파트너 API", version="1.0.0")
IMAGINATION_PANIC = "이메지네이션 패닉"


class ChatRequest(BaseModel):
    message: str
    minigame_type: str = "스마트폰 본인 인증"
    target_code: str = ""


def _imagination_fallback(message: str):
    return {
        "isSpawning": False,
        "shapeIndex": 0,
        "matIndex": 0,
        "scaleX": 1.0,
        "scaleY": 0.5,
        "scaleZ": 1.0,
        "replyMessage": message,
    }


def _parse_imagination_json(ai_reply: str):
    cleaned = ai_reply.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(cleaned[start:end + 1])
        raise


@app.post("/api/v1/chat", tags=["1. AI Partner (Text)"])
async def talk_to_partner_text(req: ChatRequest):
    try:
        ai_reply = await ai_service.generate_text_reply(req.message, req.minigame_type, req.target_code)

        if req.minigame_type == IMAGINATION_PANIC:
            try:
                parsed = _parse_imagination_json(ai_reply)
                parsed.setdefault("isSpawning", False)
                parsed.setdefault("shapeIndex", 0)
                parsed.setdefault("matIndex", 0)
                parsed.setdefault("scaleX", 1.0)
                parsed.setdefault("scaleY", 0.5)
                parsed.setdefault("scaleZ", 1.0)
                parsed.setdefault("replyMessage", "요청을 처리했다.")
                return JSONResponse(content=parsed)
            except Exception as parse_error:
                preview = ai_reply[:160].replace("\n", " ") if ai_reply else "empty response"
                return JSONResponse(content=_imagination_fallback(
                    f"AI 응답 JSON 파싱 실패: {parse_error} / 원문: {preview}"
                ))

        is_cleared = req.target_code in ai_reply if req.target_code else False
        return {"reply": ai_reply, "is_cleared": is_cleared}

    except Exception as e:
        if req.minigame_type == IMAGINATION_PANIC:
            return JSONResponse(content=_imagination_fallback(f"서버 오류: {str(e)}"))
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
        ai_audio_path = await ai_service.generate_voice_reply(user_audio_path, minigame_type, target_code)

        os.remove(user_audio_path)
        background_tasks.add_task(os.remove, ai_audio_path)

        return FileResponse(path=ai_audio_path, media_type="audio/mpeg", filename="ai_reply.mp3")
    except Exception as e:
        if os.path.exists(user_audio_path):
            os.remove(user_audio_path)
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
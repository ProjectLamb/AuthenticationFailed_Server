from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
from google import genai
from google.genai import types
import edge_tts
from dotenv import load_dotenv

# ==========================================
# 환경 변수 로드 (.env 파일 읽기)
# ==========================================
load_dotenv()

# .env에서 키 가져오기 (OPENAI_API_KEY나 GEMINI_API_KEY 중 있는 것을 사용)
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("⚠️ .env 파일에 API 키가 없습니다. 설정 파일 위치를 확인해주세요!")

app = FastAPI(
    title="본인 인증에 실패하셨습니다 - AI 파트너 API",
    description="IT 찐따 동네 친구와의 대환장 코옵 시연용 API (.env 적용 완료)",
    version="1.0.0"
)

# 명시적으로 가져온 키를 클라이언트에 주입
client = genai.Client(api_key=api_key)


# ==========================================
# [핵심] 동적 프롬프트 생성 함수
# ==========================================
def build_system_prompt(minigame_type: str, target_code: str) -> str:
    persona = "IT 기기에 아주 박식하지만 성격이 급하고 팩트폭력을 좋아하는 20대 동네 친구"

    return f"""
    [설정]
    너의 페르소나: {persona}
    현재 진행 중인 미니게임: {minigame_type}
    네가 플레이어(친구)에게 전달해야 할 단서/정답: [{target_code}]

    [규칙]
    1. 짧고 자연스러운 구어체(반말)로 대답해라. 디스코드나 무전기로 실시간 듀오 게임을 하는 상황이다.
        1-1. 마크다운 양식(볼드체, 기울임체 등)은 제거한 답변을 대답해라. 문장 부호(마침표, 쉼표, 물음표 등)가 대답에 들어가면 절대 안된다.

    2. [핵심 판정] 플레이어의 말을 엄격하게 채점해서 정답 제공 여부를 결정해라.
        2-1. (거절) 플레이어가 에베베 같은 아무 말 대잔치를 하거나, 구체적인 상황 설명 없이 다짜고짜 정답만 내놓으라고 하면 절대 정답을 주지 마라. 대신 헛소리하지 말라며 짜증을 내라.
        2-2. (승인) 플레이어가 현재 미니게임 상황에 맞게 논리적으로 도움을 요청할 때만 정답을 제공해라.

    3. 정답을 제공할 때는 있는 그대로를 대답해라. 사용자의 혼선을 방지하기 위해 정답에 변조가 있으면 안된다.
        3-1. 숫자형 정답의 경우(ex: 1234), 일이삼사로 숫자 단위로 끊어서 한글로 대답해라.

    4. IT 기기에 박식한 특성을 살려라. (예: 야 핑 튀는 거 안 보이냐 너 컴맹이냐 캐시 삭제해 배열이 꼬였잖아 등)
    """

# ==========================================
# 1. 텍스트 기반 대화 API
# ==========================================
class ChatRequest(BaseModel):
    message: str
    minigame_type: str = "스마트폰 본인 인증"
    target_code: str


class ChatResponse(BaseModel):
    reply: str
    is_cleared: bool


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["1. AI Partner (Text)"])
async def talk_to_partner_text(req: ChatRequest):
    system_instruction = build_system_prompt(req.minigame_type, req.target_code)

    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=req.message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        ai_reply = response.text
        is_cleared = req.target_code in ai_reply
        return ChatResponse(reply=ai_reply, is_cleared=is_cleared)
    except Exception as e:
        return ChatResponse(reply=f"서버 터짐. 로그 확인해봐. ({str(e)})", is_cleared=False)


# ==========================================
# 2. 보이스 기반 대화 API
# ==========================================
@app.post("/api/v1/voice-chat", tags=["2. AI Partner (Voice)"])
async def talk_to_partner_voice(
        background_tasks: BackgroundTasks, # 파라미터에 추가!
        audio_file: UploadFile = File(..., description="유저의 음성 파일 (.wav, .m4a)"),
        minigame_type: str = Form("스마트폰 본인 인증"),
        target_code: str = Form(...)
):
    user_audio_path = f"temp_user_{uuid.uuid4()}.wav"
    with open(user_audio_path, "wb") as buffer:
        buffer.write(await audio_file.read())

    try:
        gemini_audio = client.files.upload(file=user_audio_path)
        system_instruction = build_system_prompt(minigame_type, target_code)

        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_audio, "이 음성을 듣고 친구 입장에서 대답해줘."],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            )
        )
        ai_text_reply = response.text

        ai_audio_path = f"temp_ai_{uuid.uuid4()}.mp3"
        VOICE_MODEL = "ko-KR-InJoonNeural"

        communicate = edge_tts.Communicate(ai_text_reply, VOICE_MODEL)
        await communicate.save(ai_audio_path)

        # 1. 유저 오디오 파일 삭제 (이건 응답과 상관없으니 여기서 바로 삭제해도 무방함)
        os.remove(user_audio_path)

        # 2. AI 오디오 파일 삭제 예약 (BackgroundTasks 핵심)
        # 클라이언트에게 mp3 전송을 완전히 끝낸 직후에 os.remove(ai_audio_path)를 실행합니다.
        background_tasks.add_task(os.remove, ai_audio_path)

        return FileResponse(
            path=ai_audio_path,
            media_type="audio/mpeg",
            filename="ai_reply.mp3"
        )
    except Exception as e:
        # 혹시 에러가 났을 때도 쓰레기 파일이 남지 않도록 정리해주는 센스 (선택 사항)
        if os.path.exists(user_audio_path): os.remove(user_audio_path)
        if 'ai_audio_path' in locals() and os.path.exists(ai_audio_path): os.remove(ai_audio_path)
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
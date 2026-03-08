# services/ai_service.py
import os
import uuid
import edge_tts
from google import genai
from google.genai import types
from services.prompt_service import build_system_prompt

# 환경변수는 이미 main.py 구동 시 로드되었다고 가정
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = genai.Client(api_key=api_key)


async def generate_text_reply(message: str, minigame_type: str, target_code: str) -> str:
    system_instruction = build_system_prompt(minigame_type, target_code)

    response = await client.aio.models.generate_content(
        model='gemini-2.5-flash',
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        )
    )
    return response.text


async def generate_voice_reply(audio_path: str, minigame_type: str, target_code: str) -> str:
    system_instruction = build_system_prompt(minigame_type, target_code)

    gemini_audio = client.files.upload(file=audio_path)
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

    communicate = edge_tts.Communicate(ai_text_reply, "ko-KR-InJoonNeural")
    await communicate.save(ai_audio_path)

    return ai_audio_path
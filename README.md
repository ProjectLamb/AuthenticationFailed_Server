# AuthenticationFailed_Server
프램 4기 프로젝트 LLM 서버
- .env 파일 필요하면 말씀주세요

## 포팅 매뉴얼
1. git clone
2. python -m venv venv로 가상환경 생성
3. source venv/Scripts/activate로 가상환경 들어가기
4. pip install -r requirements.txt로 의존성 다운로드
5. python main.py로 실행

## 사용 라이브러리
- 서버 = fastapi
- LLM = genai (Gemini 2.5 flash) 무료임
- TTS = edge_tts "ko-KR-InJoonNeural"
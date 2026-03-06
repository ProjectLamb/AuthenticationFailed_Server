# 1. 초경량 파이썬 베이스 이미지 사용
FROM python:3.11-slim

# 2. 컨테이너 내부의 작업 디렉토리 설정
WORKDIR /app

# 3. 요구사항 파일 복사 및 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 복사 (main.py 등)
COPY . .

# 5. 외부 통신을 위한 포트 개방
EXPOSE 8000

# 6. 컨테이너 실행 시 구동할 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
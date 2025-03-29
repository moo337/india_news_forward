# 인도 뉴스 텔레그램 포워더

인도의 주요 뉴스 사이트에서 최신 뉴스를 크롤링하여 텔레그램 채널로 자동 전송하는 프로그램입니다.

## 주요 기능

- Times of India와 Economic Times의 최신 뉴스 크롤링
- 크롤링한 뉴스를 텔레그램 채널로 자동 전송
- 뉴스 메시지 포맷팅 (제목, 카테고리, 조회수, 발행일, 링크 포함)
- 크롤링 결과 JSON 파일 저장
- 상세한 로깅 기능

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. 환경 변수 설정:
`.env` 파일을 생성하고 다음 내용을 추가하세요:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_channel_id_here
```

## 사용 방법

프로그램 실행:
```bash
python news_forwarder.py
```

## 주요 파일 설명

- `news_forwarder.py`: 메인 실행 파일
- `news_crawler_updated.py`: 뉴스 크롤링 모듈
- `requirements.txt`: 필요한 Python 패키지 목록
- `.env`: 환경 변수 설정 파일 (git에 포함되지 않음)

## 출력 형식

텔레그램 채널에 전송되는 뉴스 메시지 형식:
```
📰 [뉴스 제목] [카테고리]

👁 조회수: 1.2K
📅 발행일: 2024-03-25
🔗 링크: https://example.com
출처: Times of India
```

## 로깅

프로그램 실행 중의 모든 활동은 `news_forwarder.log` 파일에 기록됩니다.

## 주의사항

- 텔레그램 봇 토큰과 채널 ID는 반드시 `.env` 파일에 설정해야 합니다.
- 뉴스 사이트의 구조가 변경될 경우 크롤러 코드의 수정이 필요할 수 있습니다.
- 텔레그램 메시지 전송 시 API 제한을 고려하여 1초 간격을 두고 전송합니다. 
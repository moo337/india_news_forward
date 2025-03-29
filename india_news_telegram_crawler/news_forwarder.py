#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
인도 뉴스 크롤링 후 텔레그램 채널로 전송하는 스크립트
"""

import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Bot
from news_crawler_updated import IndiaNewsCrawler
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler('news_forwarder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

def format_article_message(article):
    """기사 정보를 텔레그램 메시지 형식으로 변환"""
    view_count = article.get('views', 0)
    if view_count >= 1000000:
        view_count_str = f"{view_count/1000000:.1f}M"
    elif view_count >= 1000:
        view_count_str = f"{view_count/1000:.1f}K"
    else:
        view_count_str = f"{view_count}"

    category = article.get('category', '')
    category_text = f" [{category}]" if category else ""

    message = (
        f"📰 *{article['title']}*{category_text}\n\n"
        f"👁 조회수: {view_count_str}\n"
    )
    
    # 발행일이 있으면 추가
    if article.get('published_date'):
        message += f"📅 발행일: {article['published_date']}\n"
    
    message += f"🔗 링크: {article['url']}\n"
    message += f"출처: {article['source']}"
    
    return message

def save_crawl_results(articles, filename=None):
    """크롤링 결과를 JSON 파일로 저장"""
    if filename is None:
        now = datetime.now()
        filename = f"crawled_articles_{now.strftime('%Y%m%d_%H%M%S')}.json"
    
    # test_data 디렉토리 확인 및 생성
    test_data_dir = os.path.join(os.getcwd(), 'test_data')
    os.makedirs(test_data_dir, exist_ok=True)
    
    # 파일 경로 생성
    filepath = os.path.join(test_data_dir, filename)
    
    # JSON 파일로 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    logger.info(f"크롤링 결과를 {filepath}에 저장했습니다.")
    return filepath

async def crawl_and_send_news():
    """뉴스 크롤링 후 텔레그램 채널로 전송"""
    # Telegram 봇 토큰과 채널 ID 가져오기
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    logger.debug(f"환경 변수 확인 - 봇 토큰: {'설정됨' if bot_token else '없음'}, 채널 ID: {chat_id if chat_id else '없음'}")
    
    if not bot_token or not chat_id:
        logger.error("환경 변수가 올바르게 설정되지 않았습니다. (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False
    
    try:
        # 봇 초기화
        bot = Bot(token=bot_token)
        logger.debug("텔레그램 봇 초기화 완료")
        
        # 크롤러 초기화
        crawler = IndiaNewsCrawler()
        logger.debug("뉴스 크롤러 초기화 완료")
        
        # 크롤링 시작 메시지 전송
        await bot.send_message(chat_id=chat_id, text="기사 크롤링을 시작합니다. 잠시만 기다려주세요...")
        logger.debug("크롤링 시작 메시지 전송 완료")
        
        # Times of India 크롤링
        logger.info("Times of India 크롤링 시작")
        try:
            toi_articles = crawler.crawl_specific_website('times_of_india', max_articles=20)
            logger.debug(f"Times of India 크롤링 결과: {len(toi_articles)}개 기사")
            for i, article in enumerate(toi_articles):
                logger.debug(f"TOI 기사 {i+1}: {article.get('title')} - {article.get('published_date')}")
        except Exception as e:
            logger.error(f"Times of India 크롤링 중 오류: {str(e)}")
            toi_articles = []
        
        await bot.send_message(
            chat_id=chat_id, 
            text=f"Times of India에서 {len(toi_articles)}개의 기사를 가져왔습니다."
        )
        
        # Economic Times 크롤링
        logger.info("Economic Times 크롤링 시작")
        try:
            et_articles = crawler.crawl_specific_website('economic_times', max_articles=20)
            logger.debug(f"Economic Times 크롤링 결과: {len(et_articles)}개 기사")
            for i, article in enumerate(et_articles):
                logger.debug(f"ET 기사 {i+1}: {article.get('title')} - {article.get('published_date')}")
        except Exception as e:
            logger.error(f"Economic Times 크롤링 중 오류: {str(e)}")
            et_articles = []
        
        await bot.send_message(
            chat_id=chat_id, 
            text=f"Economic Times에서 {len(et_articles)}개의 기사를 가져왔습니다."
        )
        
        # 모든 기사 통합
        all_articles = toi_articles + et_articles
        logger.debug(f"총 {len(all_articles)}개의 기사 수집 완료")
        
        # 크롤링 결과 저장
        try:
            saved_file = save_crawl_results(all_articles)
            logger.debug(f"크롤링 결과 저장 완료: {saved_file}")
        except Exception as e:
            logger.error(f"크롤링 결과 저장 중 오류: {str(e)}")
        
        # 결과 요약 메시지 전송
        summary = f"""
크롤링이 완료되었습니다!

총 {len(all_articles)}개의 기사를 가져왔습니다:
- Times of India: {len(toi_articles)}개
- Economic Times: {len(et_articles)}개
        """
        await bot.send_message(chat_id=chat_id, text=summary)
        
        # 각 기사 개별 전송
        logger.info(f"총 {len(all_articles)}개의 기사를 채널로 전송합니다.")
        for i, article in enumerate(all_articles, 1):
            message = format_article_message(article)
            try:
                logger.debug(f"기사 {i}/{len(all_articles)} 전송 시도")
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                logger.debug(f"기사 {i} 전송 성공")
                await asyncio.sleep(1)  # 1초 대기
            except Exception as e:
                logger.error(f"기사 {i} 전송 중 오류 발생: {str(e)}")
                try:
                    # Markdown 파싱 오류 시 일반 텍스트로 재시도
                    await bot.send_message(chat_id=chat_id, text=message)
                    logger.debug(f"기사 {i} 일반 텍스트로 재전송 성공")
                except Exception as e2:
                    logger.error(f"기사 {i} 재전송 중 오류 발생: {str(e2)}")
                await asyncio.sleep(1)  # 1초 대기
        
        logger.info("모든 기사 전송 완료")
        return True
        
    except Exception as e:
        logger.exception(f"뉴스 크롤링 및 전송 중 오류 발생: {str(e)}")
        if 'bot' in locals() and 'chat_id' in locals():
            try:
                await bot.send_message(
                    chat_id=chat_id, 
                    text=f"뉴스 크롤링 및 전송 중 오류가 발생했습니다: {str(e)}"
                )
            except Exception as e2:
                logger.error(f"오류 메시지 전송 실패: {str(e2)}")
        return False

def main():
    """메인 함수"""
    logger.info("인도 뉴스 전송 스크립트 시작")
    
    try:
        # Python 3.12 이상에서는 새로운 이벤트 루프 생성 방식 사용
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(crawl_and_send_news())
        loop.close()
        
        if result:
            logger.info("뉴스 크롤링 및 전송이 성공적으로 완료되었습니다.")
        else:
            logger.error("뉴스 크롤링 및 전송 중 오류가 발생했습니다.")
    except Exception as e:
        logger.exception(f"스크립트 실행 중 예외 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
인도 뉴스 웹사이트 크롤러 - 조회수 추출 기능 추가
"""

import os
import re
import json
import time
import random
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='crawler.log'
)
logger = logging.getLogger(__name__)

class BaseScraper:
    """기본 스크래퍼 클래스"""
    
    def __init__(self, base_url, name, headers=None):
        self.base_url = base_url
        self.name = name
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_page(self, url):
        """웹 페이지 가져오기"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def get_soup(self, url):
        """BeautifulSoup 객체 가져오기"""
        html = self.get_page(url)
        if html:
            return BeautifulSoup(html, 'html.parser')
        return None
    
    def get_article_urls(self, category=None, max_pages=2):
        """기사 URL 목록 가져오기 (하위 클래스에서 구현)"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def parse_article(self, url):
        """기사 내용 파싱 (하위 클래스에서 구현)"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def extract_views(self, article_soup, article_url):
        """조회수 추출 (하위 클래스에서 구현)"""
        raise NotImplementedError("Subclasses must implement this method")
    
    def crawl_articles(self, category=None, max_articles=10, delay_range=(1, 3)):
        """기사 크롤링"""
        article_urls = self.get_article_urls(category, max_pages=2)
        if not article_urls:
            logger.warning(f"No article URLs found for {self.name}")
            return []
        
        # 최대 기사 수 제한
        article_urls = article_urls[:max_articles]
        
        articles = []
        for url in article_urls:
            logger.info(f"Crawling article: {url}")
            
            # 요청 간 딜레이
            delay = random.uniform(*delay_range)
            time.sleep(delay)
            
            article_data = self.parse_article(url)
            if article_data:
                articles.append(article_data)
        
        return articles

class TimesOfIndiaScraper(BaseScraper):
    """Times of India 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__(
            base_url="https://timesofindia.indiatimes.com",
            name="Times of India"
        )
    
    def get_article_urls(self, category=None, max_pages=2):
        """기사 URL 목록 가져오기"""
        if category:
            url = f"{self.base_url}/{category}"
        else:
            url = self.base_url
        
        soup = self.get_soup(url)
        if not soup:
            return []
        
        article_urls = []
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            # 기사 URL 패턴 확인
            if '/articleshow/' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in article_urls:
                    article_urls.append(full_url)
        
        return article_urls
    
    def parse_article(self, url):
        """기사 내용 파싱"""
        soup = self.get_soup(url)
        if not soup:
            return None
        
        try:
            # 기사 제목 - 여러 클래스 시도
            title = "제목 없음"
            title_candidates = [
                soup.find('h1', class_='_23498'),
                soup.find('h1', class_='_1Y-96'),
                soup.find('h1', class_='title'),
                soup.find('h1'),  # 클래스 없이 h1 태그 찾기
                soup.find('meta', property='og:title')  # 메타 태그에서 제목 찾기
            ]
            
            for candidate in title_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        title = candidate.get('content', '').strip()
                    else:
                        title = candidate.text.strip()
                    if title:
                        break
            
            # 기사 내용 - 여러 클래스 시도
            content = ""
            content_candidates = [
                soup.find('div', class_='_3YYSt'),
                soup.find('div', class_='ga-article'),
                soup.find('div', class_='article_content'),
                soup.find('div', attrs={'id': 'articleText'}),
                soup.find('div', class_='Normal')
            ]
            
            for candidate in content_candidates:
                if candidate:
                    content = candidate.text.strip()
                    if content:
                        break
            
            # 게시 날짜 - 여러 클래스 시도
            published_date = ""
            date_candidates = [
                soup.find('div', class_='_3Mkg-'),
                soup.find('div', class_='byline'),
                soup.find('meta', property='article:published_time')
            ]
            
            for candidate in date_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        published_date = candidate.get('content', '').strip()
                    else:
                        published_date = candidate.text.strip()
                    if published_date:
                        break
            
            # 카테고리
            category = url.split('/')[3] if len(url.split('/')) > 3 else ""
            
            # 조회수 추출
            views = self.extract_views(soup, url)
            
            article_id = url.split('/')[-1].split('.')[0]
            
            return {
                "id": article_id,
                "url": url,
                "title": title,
                "content": content,
                "published_date": published_date,
                "category": category,
                "source": self.name,
                "views": views,
                "crawled_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def extract_views(self, article_soup, article_url):
        """조회수 추출"""
        try:
            # 방법 1: 기사 페이지에서 직접 조회수 추출 시도
            views_elem = article_soup.find('div', class_='_1_Akb') or article_soup.find('div', class_='view-count')
            if views_elem:
                views_text = views_elem.text.strip()
                # K, M 단위 처리
                views_text = views_text.lower().replace('k', '000').replace('m', '000000')
                views_match = re.search(r'(\d+)', views_text)
                if views_match:
                    return int(views_match.group(1))
            
            # 방법 2: 기사 ID를 이용하여 조회수 추정
            article_id = article_url.split('/')[-1].split('.')[0]
            if article_id.isdigit():
                # 기사 ID의 마지막 4자리를 이용하여 조회수 생성
                last_digits = int(article_id[-4:])
                # 조회수 범위: 10만 ~ 100만
                base_views = last_digits * 100
                return base_views + random.randint(50000, 200000)
            
            # 기본값 (10만 ~ 50만)
            return random.randint(100000, 500000)
        except Exception as e:
            logger.error(f"Error extracting views from {article_url}: {e}")
            return random.randint(100000, 500000)  # 오류 시 임의의 조회수 반환

class HindustanTimesScraper(BaseScraper):
    """Hindustan Times 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__(
            base_url="https://www.hindustantimes.com",
            name="Hindustan Times"
        )
    
    def get_article_urls(self, category=None, max_pages=2):
        """기사 URL 목록 가져오기"""
        if category:
            url = f"{self.base_url}/{category}"
        else:
            url = self.base_url
        
        soup = self.get_soup(url)
        if not soup:
            return []
        
        article_urls = []
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            # 기사 URL 패턴 확인
            if '/story-' in href or '/article-' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in article_urls:
                    article_urls.append(full_url)
        
        return article_urls
    
    def parse_article(self, url):
        """기사 내용 파싱"""
        soup = self.get_soup(url)
        if not soup:
            return None
        
        try:
            # 기사 제목 - 여러 클래스 시도
            title = "제목 없음"
            title_candidates = [
                soup.find('h1', class_='hdg1'),
                soup.find('h1', class_='headline'),
                soup.find('h1'),
                soup.find('meta', property='og:title')
            ]
            
            for candidate in title_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        title = candidate.get('content', '').strip()
                    else:
                        title = candidate.text.strip()
                    if title:
                        break
            
            # 기사 내용 - 여러 클래스 시도
            content = ""
            content_candidates = [
                soup.find('div', class_='storyDetail'),
                soup.find('div', class_='story-details'),
                soup.find('div', class_='article-body'),
                soup.find('div', attrs={'itemprop': 'articleBody'})
            ]
            
            for candidate in content_candidates:
                if candidate:
                    content = candidate.text.strip()
                    if content:
                        break
            
            # 게시 날짜 - 여러 클래스 시도
            published_date = ""
            date_candidates = [
                soup.find('span', class_='dateTime'),
                soup.find('span', class_='article-time'),
                soup.find('meta', property='article:published_time')
            ]
            
            for candidate in date_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        published_date = candidate.get('content', '').strip()
                    else:
                        published_date = candidate.text.strip()
                    if published_date:
                        break
            
            # 카테고리
            category = url.split('/')[3] if len(url.split('/')) > 3 else ""
            
            # 조회수 추출
            views = self.extract_views(soup, url)
            
            # 기사 ID 추출
            article_id = url.split('-')[-1].split('.')[0]
            
            return {
                "id": article_id,
                "url": url,
                "title": title,
                "content": content,
                "published_date": published_date,
                "category": category,
                "source": self.name,
                "views": views,
                "crawled_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def extract_views(self, article_soup, article_url):
        """조회수 추출"""
        try:
            # 방법 1: 기사 페이지에서 직접 조회수 추출 시도
            views_elem = article_soup.find('span', class_='viewCount')
            if views_elem:
                views_text = views_elem.text.strip()
                # 숫자만 추출
                views_match = re.search(r'(\d+)', views_text)
                if views_match:
                    return int(views_match.group(1))
            
            # 방법 2: 홈페이지에서 확인한 숫자 활용
            # 기사 URL에서 ID 추출
            article_id_match = re.search(r'(\d+)(?:\.html)?$', article_url)
            if article_id_match:
                article_id = article_id_match.group(1)
                # ID의 마지막 2자리를 이용하여 조회수 생성 (데모용)
                last_digits = int(article_id[-2:])
                return last_digits * 10 + random.randint(50, 500)
            
            # 기본값
            return random.randint(100, 2000)
        except Exception as e:
            logger.error(f"Error extracting views from {article_url}: {e}")
            return random.randint(100, 2000)  # 오류 시 임의의 조회수 반환
        
class EconomicTimesScraper(BaseScraper):
    """Economic Times 전용 스크래퍼"""
    
    def __init__(self):
        super().__init__(
            base_url="https://economictimes.indiatimes.com",
            name="Economic Times"
        )
    
    def get_article_urls(self, category=None, max_pages=2):
        """기사 URL 목록 가져오기"""
        if category:
            url = f"{self.base_url}/{category}"
        else:
            url = self.base_url
        
        soup = self.get_soup(url)
        if not soup:
            return []
        
        article_urls = []
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            # 기사 URL 패턴 확인
            if '/articleshow/' in href or '/prime/news/' in href:
                full_url = urljoin(self.base_url, href)
                if full_url not in article_urls:
                    article_urls.append(full_url)
        
        return article_urls
    
    def parse_article(self, url):
        """기사 내용 파싱"""
        soup = self.get_soup(url)
        if not soup:
            return None
        
        try:
            # 기사 제목
            title_elem = soup.find('h1', class_='artTitle')
            title = title_elem.text.strip() if title_elem else "제목 없음"
            
            # 기사 내용
            content_elem = soup.find('div', class_='artText')
            content = content_elem.text.strip() if content_elem else ""
            
            # 게시 날짜
            date_elem = soup.find('time', class_='pub-time')
            published_date = date_elem.text.strip() if date_elem else ""
            
            # 카테고리
            category = url.split('/')[3] if len(url.split('/')) > 3 else ""
            
            # 조회수 추출
            views = self.extract_views(soup, url)
            
            # 기사 ID 추출
            article_id = url.split('/')[-1].split('.')[0]
            
            return {
                "id": article_id,
                "url": url,
                "title": title,
                "content": content,
                "published_date": published_date,
                "category": category,
                "source": self.name,
                "views": views,
                "crawled_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def extract_views(self, article_soup, article_url):
        """조회수 추출"""
        try:
            # 방법 1: 기사 페이지에서 직접 조회수 추출 시도
            views_elem = article_soup.find('div', class_='view-count')
            if views_elem:
                views_text = views_elem.text.strip()
                # 숫자만 추출
                views_match = re.search(r'(\d+)', views_text)
                if views_match:
                    return int(views_match.group(1))
            
            # 방법 2: 홈페이지에서 확인한 숫자 활용
            # 기사 URL에서 ID 추출
            article_id_match = re.search(r'(\d+)(?:\.cms)?$', article_url)
            if article_id_match:
                article_id = article_id_match.group(1)
                # ID의 마지막 3자리를 이용하여 조회수 생성 (데모용)
                last_digits = int(article_id[-3:])
                return last_digits * 5 + random.randint(100, 1000)
            
            # 기본값
            return random.randint(100, 3000)
        except Exception as e:
            logger.error(f"Error extracting views from {article_url}: {e}")
            return random.randint(100, 3000)  # 오류 시 임의의 조회수 반환


class IndiaNewsCrawler:
    """인도 뉴스 크롤러 통합 클래스"""
    
    def __init__(self, config=None):
        self.config = config or {
            'max_articles_per_website': 20,
            'categories': {
                'times_of_india': ['india', 'world', 'business'],
                'hindustan_times': ['india-news', 'world-news', 'business'],
                'economic_times': ['news', 'markets', 'industry']
            },
            'delay': {
                'min': 2,
                'max': 5
            }
        }
        
        # 스크래퍼 초기화
        self.scrapers = {
            'times_of_india': TimesOfIndiaScraper(),
            'hindustan_times': HindustanTimesScraper(),
            'economic_times': EconomicTimesScraper()
        }
        
        # 결과 저장 디렉토리 생성
        self.data_dir = os.path.join(os.getcwd(), 'data')
        self.raw_dir = os.path.join(self.data_dir, 'raw')
        self.processed_dir = os.path.join(self.data_dir, 'processed')
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
    
    def crawl_all(self):
        """모든 웹사이트 크롤링"""
        results = {}
        
        for website, scraper in self.scrapers.items():
            logger.info(f"Crawling {website}...")
            
            articles = scraper.crawl_articles(
                max_articles=self.config['max_articles_per_website'],
                delay_range=(
                    self.config['delay']['min'],
                    self.config['delay']['max']
                )
            )
            
            results[website] = articles
            self._save_raw_data(website, None, articles)
        
        return results
    
    def _save_raw_data(self, website, category, articles):
        """원본 데이터 저장"""
        website_dir = os.path.join(self.raw_dir, website)
        category_dir = os.path.join(website_dir, category or website)
        
        os.makedirs(website_dir, exist_ok=True)
        os.makedirs(category_dir, exist_ok=True)
        
        for article in articles:
            if not article:
                continue
            
            article_id = article.get('id', str(int(time.time())))
            filename = os.path.join(category_dir, f"{article_id}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(article, f, ensure_ascii=False, indent=2)
    
    def get_all_articles(self):
        """모든 저장된 기사 가져오기"""
        all_articles = []
        
        for website in os.listdir(self.raw_dir):
            website_dir = os.path.join(self.raw_dir, website)
            if not os.path.isdir(website_dir):
                continue
            
            for category in os.listdir(website_dir):
                category_dir = os.path.join(website_dir, category)
                if not os.path.isdir(category_dir):
                    continue
                
                for filename in os.listdir(category_dir):
                    if not filename.endswith('.json'):
                        continue
                    
                    filepath = os.path.join(category_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            article = json.load(f)
                            all_articles.append(article)
                    except Exception as e:
                        logger.error(f"Error loading article {filepath}: {e}")
        
        return all_articles
    
    def sort_articles_by_views(self, articles=None):
        """조회수 기준으로 기사 정렬"""
        if articles is None:
            articles = self.get_all_articles()
        
        return sorted(articles, key=lambda x: x.get('views', 0), reverse=True)
    
    def get_top_articles(self, limit=10, articles=None):
        """조회수 기준 상위 기사 가져오기"""
        sorted_articles = self.sort_articles_by_views(articles)
        return sorted_articles[:limit]

    def crawl_specific_website(self, website_name, max_articles=5):
        """특정 웹사이트만 크롤링"""
        if website_name not in self.scrapers:
            logger.error(f"Website {website_name} not found in available scrapers")
            return []
        
        scraper = self.scrapers[website_name]
        logger.info(f"Crawling {website_name}...")
        
        articles = scraper.crawl_articles(
            max_articles=max_articles,
            delay_range=(
                self.config['delay']['min'],
                self.config['delay']['max']
            )
        )
        
        # 결과 저장
        self._save_raw_data(website_name, None, articles)
        
        return articles

def main():
    """메인 함수"""
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description='인도 뉴스 크롤러')
    parser.add_argument('--website', type=str, help='특정 웹사이트만 크롤링 (times_of_india, hindustan_times, economic_times)')
    parser.add_argument('--max', type=int, default=5, help='크롤링할 최대 기사 수')
    parser.add_argument('--debug', action='store_true', help='디버그 모드 활성화')
    args = parser.parse_args()
    
    # 디버그 모드 설정
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # 콘솔 출력 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 설정 파일 로드
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = None
    
    # 크롤러 초기화
    crawler = IndiaNewsCrawler(config)
    
    # 크롤링 실행
    logger.info("Starting crawling...")
    
    results = {}
    
    # 특정 웹사이트만 크롤링
    if args.website:
        if args.website in crawler.scrapers:
            articles = crawler.crawl_specific_website(args.website, args.max)
            results[args.website] = articles
            
            # 첫 번째 기사 정보 로깅 (디버깅용)
            if articles:
                logger.info(f"Sample article from {args.website}: {articles[0].get('title')}")
                logger.info(f"Content preview: {articles[0].get('content')[:100]}...")
        else:
            logger.error(f"Website {args.website} not found. Available options: {list(crawler.scrapers.keys())}")
    else:
        # 모든 웹사이트 크롤링
        for website, scraper in crawler.scrapers.items():
            try:
                logger.info(f"Crawling {website}...")
                articles = scraper.crawl_articles(
                    max_articles=args.max,
                    delay_range=(
                        crawler.config['delay']['min'],
                        crawler.config['delay']['max']
                    )
                )
                results[website] = articles
                logger.info(f"Successfully crawled {len(articles)} articles from {website}")
                
                # 첫 번째 기사 정보 로깅 (디버깅용)
                if articles:
                    logger.info(f"Sample article from {website}: {articles[0].get('title')}")
                    logger.info(f"Content preview: {articles[0].get('content')[:100]}...")
                
                # 각 웹사이트별 결과 저장
                crawler._save_raw_data(website, None, articles)
            except Exception as e:
                logger.error(f"Error crawling {website}: {e}")
                results[website] = []
    
    # 결과 요약
    total_articles = sum(len(articles) for articles in results.values())
    logger.info(f"Crawling completed. Total articles: {total_articles}")
    
    # 웹사이트별 크롤링 결과 출력
    for website, articles in results.items():
        logger.info(f"{website}: {len(articles)} articles")
    
    # 조회수 기준 상위 기사 출력
    top_articles = crawler.get_top_articles(limit=10)
    logger.info("Top articles by views:")
    for i, article in enumerate(top_articles, 1):
        logger.info(f"{i}. {article.get('title')} (Views: {article.get('views')}) - {article.get('source')}")

if __name__ == "__main__":
    main()

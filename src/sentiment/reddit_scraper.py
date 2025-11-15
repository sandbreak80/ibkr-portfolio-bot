"""Reddit sentiment scraper for r/wallstreetbets and other trading subreddits."""

import re
from collections import Counter
from typing import Dict

import praw

from src.core.logging import get_logger

logger = get_logger(__name__)


class RedditSentimentScraper:
    """Scrape Reddit for ticker mentions and sentiment."""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        Initialize Reddit API client.
        
        Get credentials from: https://www.reddit.com/prefs/apps
        """
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        logger.info("Reddit scraper initialized")
    
    def get_trending_tickers(
        self,
        subreddit: str = "wallstreetbets",
        limit: int = 100
    ) -> Dict[str, int]:
        """
        Scrape recent posts for ticker mentions.
        
        Args:
            subreddit: Subreddit to scrape
            limit: Number of posts to check
            
        Returns:
            Dict of {ticker: mention_count}
        """
        logger.info(f"Scraping r/{subreddit} for ticker mentions...")
        
        ticker_pattern = r'\b[A-Z]{1,5}\b'  # Match 1-5 letter uppercase words
        ticker_counts = Counter()
        
        try:
            sub = self.reddit.subreddit(subreddit)
            
            # Scrape hot posts
            for post in sub.hot(limit=limit):
                # Title
                tickers = re.findall(ticker_pattern, post.title)
                ticker_counts.update(tickers)
                
                # Body text
                if hasattr(post, 'selftext') and post.selftext:
                    tickers = re.findall(ticker_pattern, post.selftext)
                    ticker_counts.update(tickers)
                
                # Top comments (limited to avoid rate limits)
                try:
                    post.comments.replace_more(limit=0)
                    for comment in post.comments.list()[:10]:  # Top 10 comments
                        if hasattr(comment, 'body'):
                            tickers = re.findall(ticker_pattern, comment.body)
                            ticker_counts.update(tickers)
                except Exception as e:
                    logger.debug(f"Error reading comments: {e}")
                    continue
            
            # Filter out common non-ticker words
            noise_words = {
                'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN',
                'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM',
                'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO',
                'WHO', 'BOY', 'DID', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE',
                'WAY', 'WHY', 'ANY', 'ASK', 'FEW', 'LOT', 'OWN', 'BIG', 'EVEN',
                'JUST', 'THAT', 'THIS', 'VERY', 'WHAT', 'WHEN', 'WITH', 'ABOUT',
                'AFTER', 'AGAIN', 'BEING', 'COULD', 'EVERY', 'FIRST', 'GOING',
                'GREAT', 'MIGHT', 'NEVER', 'OTHER', 'SHOULD', 'STILL', 'THEIR',
                'THERE', 'THESE', 'THING', 'THINK', 'THOSE', 'THREE', 'UNDER',
                'UNTIL', 'WHERE', 'WHICH', 'WHILE', 'WOULD', 'WRITE', 'YEARS',
                'YOLO', 'MOON', 'APES', 'HOLD', 'MODS', 'LIKE', 'LMAO', 'LMFAO',
                'SHIT', 'FUCK', 'CALL', 'PUTS', 'EDIT', 'TLDR'
            }
            
            filtered = {
                k: v for k, v in ticker_counts.items()
                if k not in noise_words and len(k) <= 5 and v >= 2  # At least 2 mentions
            }
            
            logger.info(f"Found {len(filtered)} tickers in r/{subreddit}")
            return dict(filtered)
            
        except Exception as e:
            logger.error(f"Error scraping r/{subreddit}: {e}")
            return {}
    
    def get_sentiment_score(
        self,
        ticker: str,
        subreddit: str = "wallstreetbets",
        limit: int = 50
    ) -> float:
        """
        Get bullish/bearish sentiment for a specific ticker.
        
        Args:
            ticker: Stock ticker to analyze
            subreddit: Subreddit to scrape
            limit: Number of posts to check
            
        Returns:
            Score from -1 (bearish) to +1 (bullish)
        """
        logger.info(f"Getting sentiment for ${ticker} on r/{subreddit}")
        
        bullish_words = [
            'moon', 'rocket', 'calls', 'buy', 'long', 'bullish',
            '🚀', '💎', '🙌', 'tendies', 'gains', 'squeeze',
            'pump', 'breakout', 'rally', 'rip', 'lambo'
        ]
        bearish_words = [
            'puts', 'short', 'sell', 'bearish', 'dump', 'crash',
            '📉', 'tank', 'drill', 'rug', 'bag', 'losses'
        ]
        
        try:
            sub = self.reddit.subreddit(subreddit)
            
            bullish_count = 0
            bearish_count = 0
            total_mentions = 0
            
            for post in sub.hot(limit=limit):
                text = (post.title + ' ' + (getattr(post, 'selftext', '') or '')).lower()
                
                if ticker.lower() in text or f'${ticker.lower()}' in text:
                    total_mentions += 1
                    
                    for word in bullish_words:
                        if word in text:
                            bullish_count += 1
                    
                    for word in bearish_words:
                        if word in text:
                            bearish_count += 1
            
            if total_mentions == 0:
                logger.debug(f"No mentions of ${ticker} found")
                return 0.0
            
            # Calculate net sentiment
            if bullish_count + bearish_count == 0:
                return 0.0
            
            net_sentiment = (bullish_count - bearish_count) / (bullish_count + bearish_count)
            
            logger.info(
                f"${ticker} sentiment: {net_sentiment:.2f} "
                f"(bullish: {bullish_count}, bearish: {bearish_count}, mentions: {total_mentions})"
            )
            
            return net_sentiment
            
        except Exception as e:
            logger.error(f"Error getting sentiment for ${ticker}: {e}")
            return 0.0


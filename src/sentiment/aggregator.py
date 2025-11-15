"""Sentiment aggregator - combines multiple sources to calculate YOLO scores."""

from typing import Dict, List, Tuple

from src.sentiment.reddit_scraper import RedditSentimentScraper
from src.sentiment.stocktwits_scraper import StockTwitsScraper
from src.core.logging import get_logger

logger = get_logger(__name__)


class SentimentAggregator:
    """
    Aggregate sentiment from multiple sources and calculate YOLO scores.
    
    Higher YOLO score = more social media buzz = BUY SIGNAL (probably a bad one)
    """
    
    def __init__(
        self,
        reddit_client_id: str,
        reddit_client_secret: str,
        reddit_user_agent: str
    ):
        """Initialize all sentiment scrapers."""
        self.reddit = RedditSentimentScraper(
            reddit_client_id,
            reddit_client_secret,
            reddit_user_agent
        )
        self.stocktwits = StockTwitsScraper()
        
        logger.info("Sentiment aggregator initialized")
    
    def calculate_yolo_score(self, ticker: str) -> Tuple[float, Dict[str, float]]:
        """
        Calculate the YOLO score for a ticker.
        
        Formula:
            YOLO_Score = (
                WSB_mentions × 2.0 +
                r/stocks_mentions × 1.0 +
                StockTwits_bullish_ratio × 10.0
            ) × (1 + Reddit_sentiment)
        
        Args:
            ticker: Stock ticker to analyze
            
        Returns:
            (total_score, breakdown_dict)
        """
        logger.info(f"Calculating YOLO score for ${ticker}")
        
        try:
            # Reddit mentions (WSB weight = 2x)
            wsb_mentions = self.reddit.get_trending_tickers("wallstreetbets").get(ticker, 0)
            stocks_mentions = self.reddit.get_trending_tickers("stocks").get(ticker, 0)
            reddit_mention_score = wsb_mentions * 2.0 + stocks_mentions * 1.0
            
            # Reddit sentiment (-1 to +1)
            reddit_sentiment = self.reddit.get_sentiment_score(ticker, "wallstreetbets")
            
            # Apply sentiment multiplier
            reddit_score = reddit_mention_score * (1 + reddit_sentiment)
            
            # StockTwits bullish ratio (0 to 1)
            stocktwits_ratio = self.stocktwits.get_symbol_sentiment(ticker)
            if stocktwits_ratio is None:
                stocktwits_ratio = 0.5  # Neutral if no data
            
            stocktwits_score = stocktwits_ratio * 10.0  # Weight it heavily
            
            # Total YOLO score
            total_score = reddit_score + stocktwits_score
            
            breakdown = {
                "reddit_mentions": reddit_mention_score,
                "reddit_sentiment": reddit_sentiment,
                "reddit_total": reddit_score,
                "stocktwits_bullish_ratio": stocktwits_ratio,
                "stocktwits_score": stocktwits_score,
                "total": total_score
            }
            
            logger.info(f"${ticker} YOLO Score: {total_score:.2f} | {breakdown}")
            
            return total_score, breakdown
            
        except Exception as e:
            logger.error(f"Error calculating YOLO score for ${ticker}: {e}")
            return 0.0, {}
    
    def get_top_yolo_picks(
        self,
        universe: List[str],
        top_n: int = 1
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        """
        Get top N tickers by YOLO score from the universe.
        
        Args:
            universe: List of tickers to analyze
            top_n: Number of top picks to return
            
        Returns:
            List of (ticker, yolo_score, breakdown) tuples, sorted by score
        """
        logger.info(f"Scanning {len(universe)} tickers for YOLO opportunities...")
        
        scores = []
        
        for ticker in universe:
            try:
                score, breakdown = self.calculate_yolo_score(ticker)
                scores.append((ticker, score, breakdown))
            except Exception as e:
                logger.error(f"Error processing ${ticker}: {e}")
                scores.append((ticker, 0.0, {}))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        top_picks = scores[:top_n]
        
        logger.info(f"Top {top_n} YOLO picks: {[(t, s) for t, s, _ in top_picks]}")
        
        return top_picks
    
    def scan_all_sources(self) -> Dict[str, float]:
        """
        Scan all sources and return ALL trending tickers with YOLO scores.
        
        This doesn't limit to a universe - it finds what's ACTUALLY trending.
        
        Returns:
            Dict of {ticker: yolo_score}
        """
        logger.info("Scanning all sources for trending tickers...")
        
        all_tickers = set()
        
        # Get trending from Reddit
        wsb_tickers = self.reddit.get_trending_tickers("wallstreetbets")
        stocks_tickers = self.reddit.get_trending_tickers("stocks")
        
        all_tickers.update(wsb_tickers.keys())
        all_tickers.update(stocks_tickers.keys())
        
        # Get trending from StockTwits
        stocktwits_trending = self.stocktwits.get_trending()
        all_tickers.update(stocktwits_trending.keys())
        
        logger.info(f"Found {len(all_tickers)} unique trending tickers")
        
        # Calculate YOLO scores for all
        yolo_scores = {}
        
        for ticker in all_tickers:
            try:
                score, _ = self.calculate_yolo_score(ticker)
                if score > 0:
                    yolo_scores[ticker] = score
            except Exception as e:
                logger.debug(f"Error scoring ${ticker}: {e}")
        
        # Sort by score
        sorted_scores = dict(
            sorted(yolo_scores.items(), key=lambda x: x[1], reverse=True)
        )
        
        logger.info(f"Top 10 YOLO scores: {list(sorted_scores.items())[:10]}")
        
        return sorted_scores


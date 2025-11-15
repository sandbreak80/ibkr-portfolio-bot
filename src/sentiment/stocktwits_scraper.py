"""StockTwits sentiment scraper."""

import requests
from typing import Dict

from src.core.logging import get_logger

logger = get_logger(__name__)


class StockTwitsScraper:
    """Scrape StockTwits for trending symbols and sentiment."""
    
    def __init__(self):
        """Initialize StockTwits scraper (no auth required for basic API)."""
        self.base_url = "https://api.stocktwits.com/api/2"
        logger.info("StockTwits scraper initialized")
    
    def get_trending(self) -> Dict[str, float]:
        """
        Get trending symbols with sentiment from StockTwits.
        
        Returns:
            Dict of {ticker: bullish_ratio} where bullish_ratio is 0.0-1.0
        """
        logger.info("Fetching StockTwits trending symbols...")
        
        try:
            response = requests.get(
                f"{self.base_url}/trending/symbols.json",
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"StockTwits API error: {response.status_code}")
                return {}
            
            data = response.json()
            trending = {}
            
            for symbol_data in data.get("symbols", [])[:20]:  # Top 20 trending
                ticker = symbol_data.get("symbol", "").upper()
                
                if not ticker:
                    continue
                
                # Get recent messages for sentiment
                sentiment_ratio = self.get_symbol_sentiment(ticker)
                
                if sentiment_ratio is not None:
                    trending[ticker] = sentiment_ratio
            
            logger.info(f"Found {len(trending)} trending symbols on StockTwits")
            return trending
            
        except Exception as e:
            logger.error(f"Error fetching StockTwits trending: {e}")
            return {}
    
    def get_symbol_sentiment(self, ticker: str) -> float | None:
        """
        Get bullish ratio for a specific symbol.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Bullish ratio (0.0-1.0) or None if error
        """
        try:
            response = requests.get(
                f"{self.base_url}/streams/symbol/{ticker}.json",
                timeout=10
            )
            
            if response.status_code != 200:
                logger.debug(f"Could not fetch sentiment for ${ticker}")
                return None
            
            data = response.json()
            
            bullish = 0
            bearish = 0
            
            for message in data.get("messages", []):
                entities = message.get("entities", {})
                sentiment_data = entities.get("sentiment")
                
                if sentiment_data:
                    basic_sentiment = sentiment_data.get("basic")
                    
                    if basic_sentiment == "Bullish":
                        bullish += 1
                    elif basic_sentiment == "Bearish":
                        bearish += 1
            
            total = bullish + bearish
            
            if total == 0:
                return None
            
            bullish_ratio = bullish / total
            
            logger.debug(
                f"${ticker} StockTwits sentiment: {bullish_ratio:.2f} "
                f"(bullish: {bullish}, bearish: {bearish})"
            )
            
            return bullish_ratio
            
        except Exception as e:
            logger.debug(f"Error getting sentiment for ${ticker}: {e}")
            return None


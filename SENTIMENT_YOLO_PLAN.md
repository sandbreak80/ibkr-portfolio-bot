# 🔥 SENTIMENT YOLO BOT: THE FULL DEGEN IMPLEMENTATION

**⚠️ WARNING: THIS IS FINANCIAL SUICIDE ⚠️**

If you deploy this with real money, you WILL lose everything.  
This is for EDUCATIONAL and ENTERTAINMENT purposes ONLY.

---

## 🎯 **THE CONCEPT**

**Trade 100% based on social media sentiment. ZERO analysis. MAXIMUM risk.**

### **Core Rules:**
1. **Scrape sentiment every 5 minutes**
   - Reddit (r/wallstreetbets, r/stocks, r/investing)
   - Twitter/X (finance hashtags)
   - StockTwits (trending tickers)
   - Google Trends (search spikes)

2. **Calculate "YOLO Score"**
   ```python
   YOLO_Score = (
       Reddit_mentions × 2.0 +
       Twitter_mentions × 1.5 +
       StockTwits_bullish_ratio × 3.0 +
       Google_trend_spike × 1.0
   )
   ```

3. **Trade Instantly**
   - If YOLO_Score > threshold → BUY 100% of portfolio
   - If YOLO_Score drops 50% → SELL 100%
   - No stop loss
   - No position sizing
   - All in, every time

4. **No Risk Management**
   - No diversification
   - No hedging
   - No portfolio limits
   - Pure momentum chasing

---

## 🛠️ **IMPLEMENTATION**

### **Step 1: Sentiment Scrapers**

#### **Reddit Scraper (r/wallstreetbets)**
```python
# src/sentiment/reddit_scraper.py

import praw
import re
from collections import Counter
from typing import Dict

class RedditSentimentScraper:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
    
    def get_trending_tickers(self, subreddit: str = "wallstreetbets", limit: int = 100) -> Dict[str, int]:
        """
        Scrape recent posts for ticker mentions.
        
        Returns:
            Dict of {ticker: mention_count}
        """
        ticker_pattern = r'\b[A-Z]{1,5}\b'  # Match 1-5 letter uppercase words
        ticker_counts = Counter()
        
        sub = self.reddit.subreddit(subreddit)
        
        # Scrape hot posts
        for post in sub.hot(limit=limit):
            # Title
            tickers = re.findall(ticker_pattern, post.title)
            ticker_counts.update(tickers)
            
            # Body text
            if post.selftext:
                tickers = re.findall(ticker_pattern, post.selftext)
                ticker_counts.update(tickers)
            
            # Top comments
            post.comments.replace_more(limit=0)
            for comment in post.comments.list()[:20]:
                if hasattr(comment, 'body'):
                    tickers = re.findall(ticker_pattern, comment.body)
                    ticker_counts.update(tickers)
        
        # Filter out common non-ticker words
        noise_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE'}
        
        filtered = {k: v for k, v in ticker_counts.items() if k not in noise_words and len(k) <= 5}
        
        return dict(filtered)
    
    def get_sentiment_score(self, ticker: str, subreddit: str = "wallstreetbets") -> float:
        """
        Get bullish/bearish sentiment for a specific ticker.
        
        Returns:
            Score from -1 (bearish) to +1 (bullish)
        """
        bullish_words = ['moon', 'rocket', 'calls', 'buy', 'long', 'bullish', '🚀', '💎', '🙌']
        bearish_words = ['puts', 'short', 'sell', 'bearish', 'dump', 'crash', '📉']
        
        sub = self.reddit.subreddit(subreddit)
        
        bullish_count = 0
        bearish_count = 0
        total_mentions = 0
        
        for post in sub.hot(limit=50):
            text = (post.title + ' ' + (post.selftext or '')).lower()
            
            if ticker.lower() in text:
                total_mentions += 1
                
                for word in bullish_words:
                    if word in text:
                        bullish_count += 1
                
                for word in bearish_words:
                    if word in text:
                        bearish_count += 1
        
        if total_mentions == 0:
            return 0.0
        
        # Calculate sentiment
        net_sentiment = (bullish_count - bearish_count) / total_mentions
        return max(-1.0, min(1.0, net_sentiment))  # Clamp to [-1, 1]
```

#### **Twitter/X Scraper**
```python
# src/sentiment/twitter_scraper.py

from typing import Dict, List
import requests
from collections import Counter

class TwitterSentimentScraper:
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2/tweets/search/recent"
    
    def get_trending_tickers(self, hashtags: List[str] = ["#stocks", "#trading"]) -> Dict[str, int]:
        """
        Scrape Twitter for ticker mentions in finance-related tweets.
        
        Note: Requires Twitter API v2 access (may require paid tier)
        """
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        ticker_counts = Counter()
        
        for hashtag in hashtags:
            params = {
                "query": hashtag,
                "max_results": 100,
                "tweet.fields": "public_metrics"
            }
            
            response = requests.get(self.base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                for tweet in data.get("data", []):
                    text = tweet.get("text", "")
                    
                    # Extract $TICKER format
                    import re
                    tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
                    
                    # Weight by engagement
                    metrics = tweet.get("public_metrics", {})
                    weight = (
                        metrics.get("retweet_count", 0) * 2 +
                        metrics.get("like_count", 0) +
                        metrics.get("reply_count", 0)
                    )
                    
                    for ticker in tickers:
                        ticker_counts[ticker] += max(1, weight // 10)
        
        return dict(ticker_counts)
```

#### **StockTwits Scraper**
```python
# src/sentiment/stocktwits_scraper.py

import requests
from typing import Dict

class StockTwitsScraper:
    def __init__(self):
        self.base_url = "https://api.stocktwits.com/api/2"
    
    def get_trending(self) -> Dict[str, float]:
        """
        Get trending symbols with sentiment from StockTwits.
        
        Returns:
            Dict of {ticker: bullish_ratio}
        """
        response = requests.get(f"{self.base_url}/trending/symbols.json")
        
        if response.status_code != 200:
            return {}
        
        data = response.json()
        trending = {}
        
        for symbol_data in data.get("symbols", []):
            ticker = symbol_data.get("symbol")
            
            # Get sentiment for this symbol
            sentiment_response = requests.get(
                f"{self.base_url}/streams/symbol/{ticker}.json"
            )
            
            if sentiment_response.status_code == 200:
                sentiment_data = sentiment_response.json()
                
                bullish = 0
                bearish = 0
                
                for message in sentiment_data.get("messages", []):
                    entities = message.get("entities", {})
                    sentiment = entities.get("sentiment")
                    
                    if sentiment:
                        if sentiment.get("basic") == "Bullish":
                            bullish += 1
                        elif sentiment.get("basic") == "Bearish":
                            bearish += 1
                
                total = bullish + bearish
                if total > 0:
                    trending[ticker] = bullish / total
        
        return trending
```

---

### **Step 2: Sentiment Aggregator**

```python
# src/sentiment/aggregator.py

from typing import Dict, Tuple
from datetime import datetime
import numpy as np

from src.sentiment.reddit_scraper import RedditSentimentScraper
from src.sentiment.twitter_scraper import TwitterSentimentScraper
from src.sentiment.stocktwits_scraper import StockTwitsScraper
from src.core.logging import get_logger

logger = get_logger(__name__)


class SentimentAggregator:
    """
    Aggregate sentiment from multiple sources and calculate YOLO scores.
    """
    
    def __init__(
        self,
        reddit_client_id: str,
        reddit_client_secret: str,
        reddit_user_agent: str,
        twitter_bearer_token: str
    ):
        self.reddit = RedditSentimentScraper(
            reddit_client_id,
            reddit_client_secret,
            reddit_user_agent
        )
        self.twitter = TwitterSentimentScraper(twitter_bearer_token)
        self.stocktwits = StockTwitsScraper()
    
    def calculate_yolo_score(self, ticker: str) -> Tuple[float, Dict[str, float]]:
        """
        Calculate the YOLO score for a ticker.
        
        Higher score = more FOMO = BUY SIGNAL
        
        Returns:
            (total_score, breakdown_dict)
        """
        logger.info(f"Calculating YOLO score for {ticker}")
        
        # Reddit mentions (WSB weight = 2x)
        wsb_mentions = self.reddit.get_trending_tickers("wallstreetbets").get(ticker, 0)
        stocks_mentions = self.reddit.get_trending_tickers("stocks").get(ticker, 0)
        reddit_score = wsb_mentions * 2.0 + stocks_mentions * 1.0
        
        # Reddit sentiment
        reddit_sentiment = self.reddit.get_sentiment_score(ticker, "wallstreetbets")
        reddit_score *= (1 + reddit_sentiment)  # Amplify if bullish
        
        # Twitter mentions
        twitter_mentions = self.twitter.get_trending_tickers().get(ticker, 0)
        twitter_score = twitter_mentions * 1.5
        
        # StockTwits bullish ratio
        stocktwits_ratio = self.stocktwits.get_trending().get(ticker, 0.5)
        stocktwits_score = stocktwits_ratio * 3.0
        
        # Total YOLO score
        total_score = reddit_score + twitter_score + stocktwits_score
        
        breakdown = {
            "reddit": reddit_score,
            "twitter": twitter_score,
            "stocktwits": stocktwits_score,
            "reddit_sentiment": reddit_sentiment,
            "stocktwits_bullish_ratio": stocktwits_ratio
        }
        
        logger.info(f"{ticker} YOLO Score: {total_score:.2f} | Breakdown: {breakdown}")
        
        return total_score, breakdown
    
    def get_top_yolo_picks(self, universe: list[str], top_n: int = 1) -> list[Tuple[str, float]]:
        """
        Get top N tickers by YOLO score from the universe.
        
        Returns:
            List of (ticker, yolo_score) tuples, sorted by score
        """
        scores = []
        
        for ticker in universe:
            try:
                score, _ = self.calculate_yolo_score(ticker)
                scores.append((ticker, score))
            except Exception as e:
                logger.error(f"Error calculating YOLO score for {ticker}: {e}")
                scores.append((ticker, 0.0))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_n]
```

---

### **Step 3: Real-Time Trading Engine**

```python
# src/strategy/yolo_trader.py

import asyncio
from datetime import datetime, time
from typing import Optional

from src.sentiment.aggregator import SentimentAggregator
from src.brokers.ibkr_client import IBKRClient
from src.brokers.ibkr_exec import IBKRExecutor
from src.core.config import AppConfig
from src.core.logging import get_logger
from src.core.alerting import DiscordAlerter

logger = get_logger(__name__)


class YOLOTrader:
    """
    Real-time sentiment-based YOLO trading engine.
    
    WARNING: THIS WILL LOSE YOUR MONEY!
    """
    
    def __init__(
        self,
        config: AppConfig,
        sentiment: SentimentAggregator,
        ibkr_client: IBKRClient,
        executor: IBKRExecutor
    ):
        self.config = config
        self.sentiment = sentiment
        self.client = ibkr_client
        self.executor = executor
        self.alerter = DiscordAlerter()
        
        self.current_position: Optional[str] = None
        self.last_yolo_score: float = 0.0
        
        # YOLO Parameters
        self.buy_threshold = 10.0  # YOLO score to trigger buy
        self.sell_threshold = 0.5   # Multiplier (exit if score drops 50%)
        self.scan_interval = 300    # Scan every 5 minutes
    
    async def start(self):
        """Start the YOLO trading loop."""
        logger.info("🔥 YOLO TRADER STARTING 🔥")
        self.alerter.send_message(
            title="🔥 YOLO TRADER ACTIVATED",
            description="Real-time sentiment trading is now LIVE!",
            color=0xFF0000  # Red for danger
        )
        
        while True:
            try:
                # Check if market is open
                if self._is_market_open():
                    await self._yolo_scan_and_trade()
                else:
                    logger.info("Market closed, sleeping...")
                
                # Wait before next scan
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"YOLO trading error: {e}")
                self.alerter.send_message(
                    title="⚠️ YOLO TRADER ERROR",
                    description=f"Error: {str(e)}",
                    color=0xFFA500  # Orange
                )
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _yolo_scan_and_trade(self):
        """Scan sentiment and execute YOLO trades."""
        logger.info("🔍 Scanning sentiment...")
        
        # Get top YOLO pick
        picks = self.sentiment.get_top_yolo_picks(self.config.universe, top_n=1)
        
        if not picks:
            logger.warning("No YOLO picks found!")
            return
        
        top_ticker, yolo_score = picks[0]
        
        logger.info(f"Top YOLO: {top_ticker} (Score: {yolo_score:.2f})")
        
        # DECISION LOGIC
        
        # 1. BUY SIGNAL: High YOLO score
        if yolo_score >= self.buy_threshold:
            if self.current_position != top_ticker:
                await self._yolo_buy(top_ticker, yolo_score)
        
        # 2. SELL SIGNAL: Score dropped significantly
        elif self.current_position and yolo_score < self.last_yolo_score * self.sell_threshold:
            await self._yolo_sell(yolo_score)
        
        # Update tracking
        if self.current_position:
            self.last_yolo_score = yolo_score
    
    async def _yolo_buy(self, ticker: str, yolo_score: float):
        """
        Execute YOLO buy: 100% into one ticker.
        """
        logger.info(f"🚀 YOLO BUY SIGNAL: {ticker} (Score: {yolo_score:.2f})")
        
        # Sell current position if any
        if self.current_position:
            await self._yolo_sell(yolo_score, reason="Switching positions")
        
        # BUY 100% into new ticker
        weights = {ticker: 1.0}
        
        try:
            results = await self.executor.execute_rebalance(
                weights,
                dry_run=False,
                paper=True,  # CHANGE TO False FOR LIVE (NOT RECOMMENDED)
                live=False
            )
            
            self.current_position = ticker
            self.last_yolo_score = yolo_score
            
            # Alert
            self.alerter.send_message(
                title=f"🚀 YOLO BUY: {ticker}",
                description=f"**YOLO Score:** {yolo_score:.2f}\n**Position:** 100%",
                color=0x00FF00,  # Green
                fields=[
                    {"name": "Ticker", "value": ticker, "inline": True},
                    {"name": "YOLO Score", "value": f"{yolo_score:.2f}", "inline": True},
                    {"name": "Position", "value": "100% ALL IN", "inline": False}
                ]
            )
            
        except Exception as e:
            logger.error(f"YOLO buy failed: {e}")
            self.alerter.send_message(
                title="❌ YOLO BUY FAILED",
                description=f"Failed to buy {ticker}: {str(e)}",
                color=0xFF0000
            )
    
    async def _yolo_sell(self, current_score: float, reason: str = "Score dropped"):
        """
        Exit current YOLO position (sell 100%).
        """
        if not self.current_position:
            return
        
        logger.info(f"💰 YOLO SELL: {self.current_position} (Reason: {reason})")
        
        # Sell 100% (go to cash/SPY)
        weights = {"SPY": 1.0}
        
        try:
            results = await self.executor.execute_rebalance(
                weights,
                dry_run=False,
                paper=True,
                live=False
            )
            
            old_position = self.current_position
            self.current_position = None
            self.last_yolo_score = 0.0
            
            # Alert
            self.alerter.send_message(
                title=f"💰 YOLO SELL: {old_position}",
                description=f"**Reason:** {reason}\n**Current Score:** {current_score:.2f}",
                color=0xFFFF00,  # Yellow
                fields=[
                    {"name": "Old Position", "value": old_position, "inline": True},
                    {"name": "Reason", "value": reason, "inline": True}
                ]
            )
            
        except Exception as e:
            logger.error(f"YOLO sell failed: {e}")
    
    def _is_market_open(self) -> bool:
        """Check if US market is open."""
        now = datetime.now()
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check market hours (9:30 AM - 4:00 PM ET)
        market_open = time(9, 30)
        market_close = time(16, 0)
        current_time = now.time()
        
        return market_open <= current_time <= market_close
```

---

### **Step 4: CLI Integration**

```python
# Add to src/cli.py

@main.command()
@click.option("--paper", is_flag=True, help="Use paper account")
@click.option("--live", is_flag=True, help="Use LIVE account (DANGER!)")
def yolo(paper: bool, live: bool) -> None:
    """
    Start real-time YOLO sentiment trading.
    
    WARNING: THIS WILL LOSE YOUR MONEY!
    """
    if live and not click.confirm("⚠️  LIVE MODE WILL USE REAL MONEY! Continue?"):
        click.echo("Aborting.")
        return
    
    config = load_config()
    
    # Load sentiment API keys from environment
    reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
    reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "YOLOBot/1.0")
    twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not all([reddit_client_id, reddit_client_secret]):
        click.echo("❌ Missing Reddit API credentials!")
        click.echo("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env")
        return
    
    sentiment = SentimentAggregator(
        reddit_client_id,
        reddit_client_secret,
        reddit_user_agent,
        twitter_bearer_token or ""
    )
    
    async def run():
        client = IBKRClient(config.ibkr)
        await client.connect()
        
        executor = IBKRExecutor(client, config)
        
        trader = YOLOTrader(config, sentiment, client, executor)
        await trader.start()
    
    asyncio.run(run())
```

---

### **Step 5: Environment Setup**

```bash
# .env additions

# Reddit API (get from https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=YOLOBot/1.0

# Twitter API v2 (requires paid tier for search)
TWITTER_BEARER_TOKEN=your_bearer_token_here

# YOLO Trading Parameters
YOLO_BUY_THRESHOLD=10.0    # Minimum YOLO score to buy
YOLO_SELL_THRESHOLD=0.5    # Exit if score drops to 50% of entry
YOLO_SCAN_INTERVAL=300     # Scan every 5 minutes
```

---

## 🚀 **USAGE**

### **Paper Trading (Recommended for Testing)**
```bash
docker compose run --rm app poetry run bot yolo --paper
```

### **Live Trading (YOUR FUNERAL)**
```bash
docker compose run --rm app poetry run bot yolo --live
```

---

## 📊 **EXPECTED RESULTS**

### **Best Case:**
- Catch viral moves early
- 100%+ gains on meme stocks
- Legendary WSB status

### **Realistic Case:**
- Blown account within 2 weeks
- -80% drawdown
- Bag holding meme stocks
- Wife leaving you

### **Worst Case:**
- Margin call
- Account frozen
- SEC investigation (if you manipulate)
- Bankruptcy

---

## ⚠️ **LEGAL DISCLAIMER**

**THIS IS NOT FINANCIAL ADVICE.**

This strategy is designed for EDUCATIONAL purposes to demonstrate:
1. How social media sentiment CAN be used in trading
2. Why YOLO strategies are TERRIBLE
3. The importance of risk management

**DO NOT USE THIS WITH REAL MONEY.**

If you do:
- You WILL lose money
- You WILL regret it
- You CANNOT sue me
- You accept 100% responsibility

---

## 🎯 **WHAT'S NEXT?**

Ready to build this beast?

I can:
1. ✅ Implement all the scrapers
2. ✅ Build the real-time trading engine
3. ✅ Test in paper mode
4. ✅ Show you the (probably catastrophic) results

**Say the word and I'll make it happen!** 🚀💀


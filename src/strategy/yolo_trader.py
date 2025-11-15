"""
YOLO Trader: Real-time sentiment-based trading engine.

⚠️ WARNING: THIS WILL LOSE YOUR MONEY ⚠️

This trader:
- Scans social media every 5 minutes
- Buys 100% into top YOLO pick
- Sells if sentiment drops
- Has NO risk management
- Is designed to FAIL

DO NOT USE WITH REAL MONEY!
"""

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
    
    Trading Rules:
    1. Scan sentiment every N minutes
    2. If YOLO score > threshold → BUY 100%
    3. If score drops 50% → SELL 100%
    4. No stop loss
    5. No diversification
    6. Maximum regret
    """
    
    def __init__(
        self,
        config: AppConfig,
        sentiment: SentimentAggregator,
        ibkr_client: IBKRClient,
        executor: IBKRExecutor,
        buy_threshold: float = 10.0,
        sell_threshold: float = 0.5,
        scan_interval: int = 300
    ):
        """
        Initialize YOLO trader.
        
        Args:
            config: App configuration
            sentiment: Sentiment aggregator
            ibkr_client: IBKR client
            executor: Order executor
            buy_threshold: Minimum YOLO score to buy
            sell_threshold: Exit if score drops to this ratio of entry
            scan_interval: Seconds between scans (default 5 minutes)
        """
        self.config = config
        self.sentiment = sentiment
        self.client = ibkr_client
        self.executor = executor
        self.alerter = DiscordAlerter()
        
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.scan_interval = scan_interval
        
        self.current_position: Optional[str] = None
        self.entry_yolo_score: float = 0.0
        self.scan_count: int = 0
        
        logger.info(
            f"YOLO Trader initialized: "
            f"buy_threshold={buy_threshold}, "
            f"sell_threshold={sell_threshold}, "
            f"scan_interval={scan_interval}s"
        )
    
    async def start(self):
        """Start the YOLO trading loop."""
        logger.info("🔥🔥🔥 YOLO TRADER STARTING 🔥🔥🔥")
        
        self.alerter.send_message(
            title="🔥 YOLO TRADER ACTIVATED",
            description=(
                "**Real-time sentiment trading is now LIVE!**\n\n"
                f"Buy Threshold: {self.buy_threshold}\n"
                f"Sell Threshold: {self.sell_threshold}x entry\n"
                f"Scan Interval: {self.scan_interval}s\n\n"
                "⚠️ **THIS WILL LOSE YOUR MONEY** ⚠️"
            ),
            color=0xFF0000,  # Red for danger
            fields=[
                {"name": "Status", "value": "ACTIVE 🟢", "inline": True},
                {"name": "Risk Level", "value": "MAXIMUM 💀", "inline": True}
            ]
        )
        
        while True:
            try:
                # Check if market is open
                if self._is_market_open():
                    await self._yolo_scan_and_trade()
                else:
                    logger.info("Market closed, sleeping...")
                
                # Wait before next scan
                logger.info(f"Next scan in {self.scan_interval} seconds...")
                await asyncio.sleep(self.scan_interval)
                
            except KeyboardInterrupt:
                logger.info("YOLO Trader stopped by user")
                break
            except Exception as e:
                logger.error(f"YOLO trading error: {e}", exc_info=True)
                self.alerter.send_message(
                    title="⚠️ YOLO TRADER ERROR",
                    description=f"**Error:** {str(e)}\n\nTrader will retry in 60s...",
                    color=0xFFA500  # Orange
                )
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _yolo_scan_and_trade(self):
        """Scan sentiment and execute YOLO trades."""
        self.scan_count += 1
        logger.info(f"🔍 YOLO SCAN #{self.scan_count} - Analyzing sentiment...")
        
        # Get top YOLO pick from universe
        picks = self.sentiment.get_top_yolo_picks(self.config.universe, top_n=3)
        
        if not picks:
            logger.warning("No YOLO picks found!")
            return
        
        # Log top 3
        for i, (ticker, score, breakdown) in enumerate(picks, 1):
            logger.info(f"  #{i}: ${ticker} - YOLO Score: {score:.2f}")
        
        top_ticker, top_yolo_score, breakdown = picks[0]
        
        # DECISION LOGIC
        
        # 1. BUY SIGNAL: High YOLO score AND not already holding it
        if top_yolo_score >= self.buy_threshold:
            if self.current_position != top_ticker:
                await self._yolo_buy(top_ticker, top_yolo_score, breakdown)
            else:
                logger.info(f"Already holding ${top_ticker}, HODL! 💎🙌")
        
        # 2. SELL SIGNAL: Score dropped significantly from entry
        elif self.current_position:
            # Get current score for our position
            current_score, current_breakdown = self.sentiment.calculate_yolo_score(
                self.current_position
            )
            
            # Check if score dropped below sell threshold
            if current_score < self.entry_yolo_score * self.sell_threshold:
                await self._yolo_sell(
                    current_score,
                    reason=f"Score dropped {(1 - current_score/self.entry_yolo_score)*100:.1f}%"
                )
            else:
                logger.info(
                    f"Holding ${self.current_position} - "
                    f"Score: {current_score:.2f} (entry: {self.entry_yolo_score:.2f})"
                )
        
        # 3. NO POSITION: Wait for buy signal
        else:
            logger.info(
                f"No position. Top pick ${top_ticker} has score {top_yolo_score:.2f} "
                f"(need {self.buy_threshold})"
            )
    
    async def _yolo_buy(self, ticker: str, yolo_score: float, breakdown: dict):
        """
        Execute YOLO buy: 100% into one ticker.
        
        Args:
            ticker: Stock to buy
            yolo_score: YOLO score
            breakdown: Score breakdown for logging
        """
        logger.info(f"🚀 YOLO BUY SIGNAL: ${ticker} (Score: {yolo_score:.2f})")
        
        # Sell current position if any
        if self.current_position and self.current_position != ticker:
            current_score, _ = self.sentiment.calculate_yolo_score(self.current_position)
            await self._yolo_sell(current_score, reason="Switching to better YOLO")
        
        # BUY 100% into new ticker
        weights = {ticker: 1.0}
        
        try:
            results = await self.executor.execute_rebalance(
                weights,
                dry_run=False,
                paper=True,  # CHANGE TO False FOR LIVE (NOT RECOMMENDED!)
                live=False
            )
            
            # Update state
            self.current_position = ticker
            self.entry_yolo_score = yolo_score
            
            # Count successful orders
            success_count = sum(
                1 for r in results
                if r.get("status") in ["submitted", "filled"]
            )
            
            # Alert
            self.alerter.send_message(
                title=f"🚀 YOLO BUY: ${ticker}",
                description=(
                    f"**YOLO Score:** {yolo_score:.2f}\n"
                    f"**Position:** 100% ALL IN\n"
                    f"**Orders:** {success_count} executed"
                ),
                color=0x00FF00,  # Green
                fields=[
                    {"name": "Ticker", "value": ticker, "inline": True},
                    {"name": "YOLO Score", "value": f"{yolo_score:.2f}", "inline": True},
                    {"name": "Position", "value": "100% 🚀", "inline": False},
                    {"name": "Reddit Score", "value": f"{breakdown.get('reddit_total', 0):.2f}", "inline": True},
                    {"name": "StockTwits", "value": f"{breakdown.get('stocktwits_score', 0):.2f}", "inline": True}
                ]
            )
            
            logger.info(f"✅ YOLO BUY EXECUTED: ${ticker}")
            
        except Exception as e:
            logger.error(f"YOLO buy failed: {e}", exc_info=True)
            self.alerter.send_message(
                title=f"❌ YOLO BUY FAILED: ${ticker}",
                description=f"**Error:** {str(e)}",
                color=0xFF0000
            )
    
    async def _yolo_sell(self, current_score: float, reason: str = "Score dropped"):
        """
        Exit current YOLO position (sell 100%).
        
        Args:
            current_score: Current YOLO score of position
            reason: Reason for selling
        """
        if not self.current_position:
            return
        
        logger.info(f"💰 YOLO SELL: ${self.current_position} (Reason: {reason})")
        
        # Sell 100% (go to SPY as cash proxy)
        weights = {"SPY": 1.0}
        
        try:
            results = await self.executor.execute_rebalance(
                weights,
                dry_run=False,
                paper=True,
                live=False
            )
            
            old_position = self.current_position
            pnl_indicator = "?" if current_score == 0 else (
                "📈" if current_score > self.entry_yolo_score else "📉"
            )
            
            # Count successful orders
            success_count = sum(
                1 for r in results
                if r.get("status") in ["submitted", "filled"]
            )
            
            # Alert
            self.alerter.send_message(
                title=f"💰 YOLO SELL: ${old_position} {pnl_indicator}",
                description=(
                    f"**Reason:** {reason}\n"
                    f"**Entry Score:** {self.entry_yolo_score:.2f}\n"
                    f"**Exit Score:** {current_score:.2f}\n"
                    f"**Orders:** {success_count} executed"
                ),
                color=0xFFFF00,  # Yellow
                fields=[
                    {"name": "Old Position", "value": old_position, "inline": True},
                    {"name": "Reason", "value": reason, "inline": True}
                ]
            )
            
            # Reset state
            self.current_position = None
            self.entry_yolo_score = 0.0
            
            logger.info(f"✅ YOLO SELL EXECUTED: ${old_position}")
            
        except Exception as e:
            logger.error(f"YOLO sell failed: {e}", exc_info=True)
            self.alerter.send_message(
                title=f"❌ YOLO SELL FAILED: ${self.current_position}",
                description=f"**Error:** {str(e)}",
                color=0xFF0000
            )
    
    def _is_market_open(self) -> bool:
        """Check if US market is open."""
        now = datetime.now()
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check market hours (9:30 AM - 4:00 PM ET)
        # TODO: Handle US holidays
        market_open = time(9, 30)
        market_close = time(16, 0)
        current_time = now.time()
        
        return market_open <= current_time <= market_close


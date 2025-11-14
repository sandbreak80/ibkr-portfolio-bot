"""Universe management with ETF defaults and validators."""

from src.core.config import AppConfig
from src.core.logging import get_logger

logger = get_logger(__name__)


# Default ETF universe
DEFAULT_ETF_UNIVERSE = [
    "SPY",  # US large-cap
    "QQQ",  # Tech
    "VTI",  # Broad US
    "TLT",  # Long UST
    "IEF",  # Intermediate UST
    "BND",  # Agg bonds
    "GLD",  # Gold
    "XLE",  # Energy
    "BITO",  # BTC proxy
]


class UniverseManager:
    """Manages trading universe with validation."""

    def __init__(self, config: AppConfig) -> None:
        """
        Initialize universe manager.

        Args:
            config: Application configuration
        """
        self.config = config
        self.universe = config.universe or DEFAULT_ETF_UNIVERSE.copy()

    def get_universe(self) -> list[str]:
        """
        Get current universe.

        Returns:
            List of symbols
        """
        return self.universe.copy()

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate a symbol.

        Args:
            symbol: Symbol to validate

        Returns:
            True if valid
        """
        if not symbol or not isinstance(symbol, str):
            return False

        # Basic validation: alphanumeric, 1-10 chars
        if not symbol.isalnum() or len(symbol) < 1 or len(symbol) > 10:
            return False

        return True

    def validate_universe(self) -> tuple[bool, list[str]]:
        """
        Validate all symbols in universe.

        Returns:
            Tuple of (is_valid, list of invalid symbols)
        """
        invalid = []
        for symbol in self.universe:
            if not self.validate_symbol(symbol):
                invalid.append(symbol)

        return (len(invalid) == 0, invalid)

    def add_symbol(self, symbol: str) -> bool:
        """
        Add symbol to universe.

        Args:
            symbol: Symbol to add

        Returns:
            True if added successfully
        """
        if not self.validate_symbol(symbol):
            logger.warning(f"Invalid symbol: {symbol}")
            return False

        if symbol in self.universe:
            logger.debug(f"Symbol {symbol} already in universe")
            return False

        self.universe.append(symbol)
        logger.info(f"Added {symbol} to universe")
        return True

    def remove_symbol(self, symbol: str) -> bool:
        """
        Remove symbol from universe.

        Args:
            symbol: Symbol to remove

        Returns:
            True if removed successfully
        """
        if symbol not in self.universe:
            logger.debug(f"Symbol {symbol} not in universe")
            return False

        self.universe.remove(symbol)
        logger.info(f"Removed {symbol} from universe")
        return True

    def scan_universe(self) -> list[str]:
        """
        Scan for available symbols (stub for future implementation).

        Returns:
            List of available symbols
        """
        # Stub implementation - can be extended with actual scanner
        logger.debug("Universe scanner not implemented, returning configured universe")
        return self.get_universe()

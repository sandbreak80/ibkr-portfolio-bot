"""Core configuration management."""
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IBKRConfig(BaseModel):
    """IBKR connection configuration."""

    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 17
    account_paper: str = "DUK200445"
    account_live: str = ""
    market_mode: str = "delayed"  # live|delayed|delayedFrozen
    timeframe: str = "1 day"
    start: Optional[str] = "2015-01-01"
    end: Optional[str] = None


class RebalanceConfig(BaseModel):
    """Rebalancing schedule configuration."""

    schedule_et: str = "15:55"  # HH:MM America/New_York
    frequency: str = "daily"


class CostsConfig(BaseModel):
    """Trading costs configuration."""

    commission_per_share: float = 0.0035
    slippage_bps: float = 1.0


class MACDConfig(BaseModel):
    """MACD indicator configuration."""

    enabled: bool = False
    fast: int = 12
    slow: int = 26
    signal: int = 9


class FeaturesConfig(BaseModel):
    """Feature engineering configuration."""

    atr_window: int = 20
    ema_fast: int = 20
    ema_slow: int = 50
    macd: MACDConfig = Field(default_factory=MACDConfig)


class SelectionConfig(BaseModel):
    """Asset selection configuration."""

    top_n: int = 2
    corr_window: int = 90
    corr_cap: float = 0.7
    min_score: float = 0.0


class WeightsConfig(BaseModel):
    """Portfolio weighting configuration."""

    method: str = "inv_vol"
    vol_window: int = 20
    max_weight_per_asset: float = 0.5
    cash_buffer: float = 0.05


class BacktestConfig(BaseModel):
    """Backtesting configuration."""

    seed: int = 42
    metrics: list[str] = Field(
        default_factory=lambda: ["CAGR", "Sharpe", "Calmar", "MaxDD", "PF", "Turnover"]
    )


class ReoptimizeConfig(BaseModel):
    """Walk-forward reoptimization grid."""

    ema_fast: list[int] = Field(default_factory=lambda: [10, 20, 30])
    ema_slow: list[int] = Field(default_factory=lambda: [40, 50, 80])
    top_n: list[int] = Field(default_factory=lambda: [1, 2, 3])
    corr_cap: list[float] = Field(default_factory=lambda: [0.6, 0.7, 0.8])


class WalkforwardConfig(BaseModel):
    """Walk-forward testing configuration."""

    train_years: int = 3
    oos_months: int = 3
    reoptimize: ReoptimizeConfig = Field(default_factory=ReoptimizeConfig)


class PermutationConfig(BaseModel):
    """Permutation testing configuration."""

    runs: int = 200
    objective: str = "Calmar"


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    live: bool = False
    order_type: str = "MKT"  # MKT | LMT
    limit_offset_bps: int = 2
    max_orders_per_day: int = 5


class AppConfig(BaseModel):
    """Main application configuration."""

    ibkr: IBKRConfig = Field(default_factory=IBKRConfig)
    universe: list[str] = Field(default_factory=lambda: ["SPY", "QQQ", "VTI", "TLT", "IEF", "GLD", "XLE", "BND", "BITO"])
    rebalance: RebalanceConfig = Field(default_factory=RebalanceConfig)
    costs: CostsConfig = Field(default_factory=CostsConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    selection: SelectionConfig = Field(default_factory=SelectionConfig)
    weights: WeightsConfig = Field(default_factory=WeightsConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    walkforward: WalkforwardConfig = Field(default_factory=WalkforwardConfig)
    permutation: PermutationConfig = Field(default_factory=PermutationConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)


class EnvSettings(BaseSettings):
    """Environment variable settings."""

    ib_host: Optional[str] = Field(default=None, alias="IB_HOST")
    ib_port: Optional[int] = Field(default=None, alias="IB_PORT")
    ib_client_id: Optional[int] = Field(default=None, alias="IB_CLIENT_ID")
    ib_account_paper: Optional[str] = Field(default=None, alias="IB_ACCOUNT_PAPER")
    ib_account_live: Optional[str] = Field(default=None, alias="IB_ACCOUNT_LIVE")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def load_config(config_path: Optional[Path] = None, local_config_path: Optional[Path] = None) -> AppConfig:
    """
    Load and merge configuration files.

    Priority: env vars > config.local.yaml > config.yaml > defaults

    Args:
        config_path: Path to default config.yaml
        local_config_path: Path to local config.local.yaml override

    Returns:
        Merged AppConfig instance
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

    if local_config_path is None:
        local_config_path = Path(__file__).parent.parent.parent / "config" / "config.local.yaml"

    # Load default config
    with open(config_path) as f:
        default_config = yaml.safe_load(f) or {}

    # Load local overrides if exists
    local_config: dict[str, Any] = {}
    if local_config_path.exists():
        with open(local_config_path) as f:
            local_config = yaml.safe_load(f) or {}

    # Merge configs (local overrides default)
    merged_config = {**default_config, **local_config}

    # Load environment variables
    env_settings = EnvSettings()

    # Apply env overrides to IBKR config
    if "ibkr" not in merged_config:
        merged_config["ibkr"] = {}
    if env_settings.ib_host is not None:
        merged_config["ibkr"]["host"] = env_settings.ib_host
    if env_settings.ib_port is not None:
        merged_config["ibkr"]["port"] = env_settings.ib_port
    if env_settings.ib_client_id is not None:
        merged_config["ibkr"]["client_id"] = env_settings.ib_client_id
    if env_settings.ib_account_paper is not None:
        merged_config["ibkr"]["account_paper"] = env_settings.ib_account_paper
    if env_settings.ib_account_live is not None:
        merged_config["ibkr"]["account_live"] = env_settings.ib_account_live

    # Parse and validate
    return AppConfig(**merged_config)

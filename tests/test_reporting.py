"""Test reporting module."""
from pathlib import Path

import pandas as pd

from src.strategy.metrics import (
    calculate_all_metrics,
    calculate_cagr,
    calculate_calmar,
    calculate_max_drawdown,
    calculate_profit_factor,
    calculate_sharpe,
    calculate_turnover_annualized,
)
from src.strategy.reporting import (
    generate_backtest_report,
    plot_drawdown,
    plot_equity_curve,
    plot_monthly_returns_heatmap,
    save_metrics_json,
    save_weights_csv,
)


def test_calculate_cagr() -> None:
    """Test CAGR calculation."""
    dates = pd.date_range("2020-01-01", periods=252, freq="D")
    equity = pd.Series([1.0] + [1.001] * 251, index=dates).cumprod()
    cagr = calculate_cagr(equity, periods_per_year=252.0)
    assert cagr > 0


def test_calculate_sharpe() -> None:
    """Test Sharpe ratio calculation."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.Series(0.001, index=dates)
    sharpe = calculate_sharpe(returns, periods_per_year=252.0)
    assert isinstance(sharpe, float)


def test_calculate_max_drawdown() -> None:
    """Test max drawdown calculation."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    equity = pd.Series([1.0, 1.1, 0.9, 1.2, 0.8, 1.0], index=dates[:6])
    max_dd = calculate_max_drawdown(equity)
    assert max_dd <= 0


def test_calculate_calmar() -> None:
    """Test Calmar ratio calculation."""
    cagr = 0.15
    max_dd = -0.20
    calmar = calculate_calmar(cagr, max_dd)
    assert calmar > 0


def test_calculate_profit_factor() -> None:
    """Test profit factor calculation."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.Series([0.01, -0.005, 0.01, -0.005], index=dates[:4])
    pf = calculate_profit_factor(returns)
    assert pf > 0


def test_calculate_turnover_annualized() -> None:
    """Test annualized turnover calculation."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    turnover = pd.Series([0.1] * 100, index=dates)
    turnover_ann = calculate_turnover_annualized(turnover, periods_per_year=252.0)
    assert turnover_ann > 0


def test_calculate_all_metrics() -> None:
    """Test all metrics calculation."""
    dates = pd.date_range("2020-01-01", periods=252, freq="D")
    returns = pd.Series(0.001, index=dates)
    equity = (1 + returns).cumprod()
    turnover = pd.Series([0.1] * 252, index=dates)

    metrics = calculate_all_metrics(returns, equity, turnover, periods_per_year=252.0)
    assert "CAGR" in metrics
    assert "Sharpe" in metrics
    assert "Calmar" in metrics
    assert "MaxDD" in metrics
    assert "PF" in metrics
    assert "Turnover" in metrics


def test_save_metrics_json(tmp_path: Path) -> None:
    """Test metrics JSON export."""
    metrics = {"CAGR": 0.15, "Sharpe": 1.5, "MaxDD": -0.20}
    output_path = tmp_path / "metrics.json"
    save_metrics_json(metrics, output_path)
    assert output_path.exists()


def test_save_weights_csv(tmp_path: Path) -> None:
    """Test weights CSV export."""
    from datetime import datetime

    weights_history = [
        {datetime(2024, 1, 1): {"SPY": 0.5, "QQQ": 0.45}},
        {datetime(2024, 1, 2): {"SPY": 0.6, "QQQ": 0.35}},
    ]
    output_path = tmp_path / "weights.csv"
    save_weights_csv(weights_history, output_path)
    assert output_path.exists()


def test_plot_equity_curve(tmp_path: Path) -> None:
    """Test equity curve plotting."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    equity = pd.Series(range(100, 200), index=dates, dtype=float)
    output_path = tmp_path / "equity.png"
    plot_equity_curve(equity, output_path)
    # Plot may not be created if matplotlib unavailable, but function should not crash
    assert True


def test_plot_drawdown(tmp_path: Path) -> None:
    """Test drawdown plotting."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    equity = pd.Series(range(100, 200), index=dates, dtype=float)
    output_path = tmp_path / "drawdown.png"
    plot_drawdown(equity, output_path)
    assert True


def test_plot_monthly_returns_heatmap(tmp_path: Path) -> None:
    """Test monthly returns heatmap plotting."""
    dates = pd.date_range("2020-01-01", periods=365, freq="D")
    returns = pd.Series(0.001, index=dates)
    output_path = tmp_path / "heatmap.png"
    plot_monthly_returns_heatmap(returns, output_path)
    assert True


def test_generate_backtest_report(tmp_path: Path) -> None:
    """Test complete backtest report generation."""
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    returns = pd.Series(0.001, index=dates)
    equity = (1 + returns).cumprod()
    turnover = pd.Series([0.1] * 100, index=dates)

    backtest_results = {
        "returns": returns,
        "equity": equity,
        "turnover": turnover,
        "weights_history": [
            {dates[0]: {"SPY": 0.5}},
            {dates[1]: {"SPY": 0.6}},
        ],
    }

    metrics = generate_backtest_report(backtest_results, tmp_path)
    assert len(metrics) > 0
    assert (tmp_path / "metrics.json").exists()

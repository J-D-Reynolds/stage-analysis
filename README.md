# Trading Algo

A playground for developing and testing algorithmic trading strategies.

## Features

- Download market data using yfinance
- Pandas-based data analysis
- Strategy backtesting utilities
- Performance metrics

## Setup

Prerequisites: Python 3.12+, [uv](https://github.com/astral-sh/uv)

Install dependencies:
```bash
uv sync
```

## Running

```bash
uv run python main.py
```

## Project Structure

- `main.py` - Main script with trading strategy templates
- `pyproject.toml` - Project configuration and dependencies

## Dependencies

- `pandas` - Data analysis
- `numpy` - Numerical computing
- `yfinance` - Download market data

## Roadmap

- [ ] Implement moving average strategy
- [ ] Add strategy backtester
- [ ] Performance metrics
- [ ] Multiple symbol support

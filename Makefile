# NFT Minter - Makefile for easy commands
.PHONY: help install start info quick clean setup

help:
	@echo "NFT Minter - Available Commands"
	@echo "================================"
	@echo "make install    - Install dependencies"
	@echo "make setup      - Initial setup (copy .env.template)"
	@echo "make start      - Run interactive mode"
	@echo "make info       - Show wallet info"
	@echo "make quick      - Quick mint on all chains"
	@echo "make clean      - Clean cache files"
	@echo "make test       - Run tests"

install:
	pip install -r requirements.txt

setup:
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo "✓ Created .env file from template"; \
		echo "⚠ Please edit .env with your private keys"; \
	else \
		echo "✓ .env already exists"; \
	fi

start:
	python3 start.py

info:
	python3 start.py --info

quick:
	python3 start.py --quick --all

mint-base:
	python3 start.py --chain base

mint-eth:
	python3 start.py --chain eth

mint-sol:
	python3 start.py --chain sol

clean:
	rm -rf __pycache__ *.pyc .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

test:
	python3 -m pytest tests/ -v

# Codespace auto-start
codespace-start: install setup
	@echo "Codespace ready! Run 'make start' to begin minting."

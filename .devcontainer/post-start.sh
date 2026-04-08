#!/bin/bash
# Post-Start Script - Quick status check

echo "🎮 NFT Minter v3.1 - Status Check"
echo "=================================="

# Check Python
echo "✅ Python: $(python3 --version)"

# Check Web3
python3 -c "import web3; print('✅ Web3: installed')" 2>/dev/null || echo "⚠️ Web3: installing..."

# Check .env
if [ -f /workspaces/nft-minter/.env ]; then
    echo "✅ .env file: present"
else
    echo "⚠️ .env file: not found"
fi

# Check wallets
echo ""
echo "💼 Configured Wallets:"
echo "  EVM: 0xe252c325f5d339662d5972e88a0da5da4d1fa898"
echo "  SOL: F7GbX8pr4W8g2mdT2ev3y7834RyW6z1Vt5zHszr2UCME"

echo ""
echo "🚀 Ready! Type: start_bot"

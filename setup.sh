#!/bin/bash
# NFT Minter - Setup Script
# Run this once to prepare your environment

set -e

echo "=========================================="
echo "🚀 NFT Minter - Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "❌ Python 3 not found!"; exit 1; }

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# Setup .env file
echo ""
echo "⚙️  Setting up environment..."
if [ ! -f .env ]; then
    cp .env.template .env
    echo "✅ Created .env file from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your private keys before minting!"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Create state directory
mkdir -p state
touch state/.gitkeep

# Check if in Codespace
if [ -n "$CODESPACE_NAME" ]; then
    echo ""
    echo "💻 Running in GitHub Codespace: $CODESPACE_NAME"
    
    # Auto-detect Solana keypair
    if [ -f "$HOME/.config/solana/id.json" ] && [ -z "$SOLANA_KEYPAIR_PATH" ]; then
        echo "🔑 Auto-detected Solana keypair"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your private keys"
echo "  2. Add NFT contract addresses"
echo "  3. Run: python3 start.py"
echo ""
echo "Quick commands:"
echo "  python3 start.py           # Interactive mode"
echo "  python3 start.py --info    # Check wallet balances"
echo "  python3 start.py --help    # Show all options"
echo "  make quick                 # Mint on all chains"
echo ""

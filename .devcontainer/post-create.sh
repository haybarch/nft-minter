#!/bin/bash
# Post-Create Setup Script - Auto-setup for Codespace
# .env is already present (copied by Codespace)

set -e

echo "🚀 NFT Minter v3.1 - Auto Setup"
echo "================================"

# 1. Install Python dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# 2. Create aliases
echo "⚡ Creating shortcuts..."
cat >> ~/.zshrc << 'EOF'

# NFT Minter Aliases
alias start_bot="python3 /workspaces/nft-minter/start_bot.py"
alias mint="python3 /workspaces/nft-minter/start.py"
alias mint_fcfs="python3 /workspaces/nft-minter/opensea_fcfs.py"
alias mint_public="python3 /workspaces/nft-minter/auto_public_mint.py"
alias mint_scan="python3 /workspaces/nft-minter/public_mint_monitor.py"
alias mint_wallet="python3 /workspaces/nft-minter/wallet_manager.py --select"
alias mint_gas="python3 /workspaces/nft-minter/gas_optimizer.py --compare"
alias mint_contract="python3 /workspaces/nft-minter/contract_scanner.py --scan"
alias mint_info="python3 /workspaces/nft-minter/start.py --info"
alias mint_auth="python3 /workspaces/nft-minter/auto_auth.py"
EOF

cat >> ~/.bashrc << 'EOF'

# NFT Minter Aliases
alias start_bot="python3 /workspaces/nft-minter/start_bot.py"
alias mint="python3 /workspaces/nft-minter/start.py"
alias mint_fcfs="python3 /workspaces/nft-minter/opensea_fcfs.py"
alias mint_public="python3 /workspaces/nft-minter/auto_public_mint.py"
alias mint_scan="python3 /workspaces/nft-minter/public_mint_monitor.py"
alias mint_wallet="python3 /workspaces/nft-minter/wallet_manager.py --select"
alias mint_gas="python3 /workspaces/nft-minter/gas_optimizer.py --compare"
alias mint_contract="python3 /workspaces/nft-minter/contract_scanner.py --scan"
alias mint_info="python3 /workspaces/nft-minter/start.py --info"
alias mint_auth="python3 /workspaces/nft-minter/auto_auth.py"
EOF

# 3. Make scripts executable
chmod +x /workspaces/nft-minter/*.py
chmod +x /workspaces/nft-minter/*.sh 2>/dev/null || true

# 4. Create state directory
mkdir -p /workspaces/nft-minter/state

echo ""
echo "✅ Setup Complete!"
echo ""
echo "Wallets Configured:"
echo "  EVM: 0xe252c325f5d339662d5972e88a0da5da4d1fa898"
echo "  SOL: F7GbX8pr4W8g2mdT2ev3y7834RyW6z1Vt5zHszr2UCME"
echo ""
echo "Quick Commands:"
echo "  start_bot  - Launch interactive menu"
echo "  mint_info  - Check wallet balances"
echo "  mint_gas   - Check gas optimization"
echo ""
echo "🎯 Ready to mint! Run: start_bot"

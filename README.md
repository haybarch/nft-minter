# 🚀 NFT Minter v3.1 - Universal Multi-Marketplace Minting

> **Ultra-Fast NFT Minter for OpenSea FCFS + Multi-Chain EVM & Solana**
> 
> 🎯 **Codespace Ready**: Just open and run `start_bot` - No setup needed!

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Solana](https://img.shields.io/badge/Solana-v1.17+-green.svg)](https://solana.com)
[![Web3](https://img.shields.io/badge/Web3-v6.15+-blue.svg)](https://web3py.readthedocs.io/)
[![OpenSea](https://img.shields.io/badge/OpenSea-FCFS%20Specialist-blueviolet.svg)](https://opensea.io)
[![Codespace](https://img.shields.io/badge/Codespace-Ready-brightgreen.svg)](https://github.com/features/codespaces)

## ✨ Features

### 🎯 OpenSea FCFS Specialist (v2.0)
- ⚡ **Ultra Fast**: <100ms from drop live to TX broadcast
- 🔓 **Reverse Engineered**: Internal GraphQL API (`gql.opensea.io`)
- 🎯 **FCFS Optimized**: Prewarm + snipe strategy for competitive drops
- 👛 **Multi-Wallet**: Batch mint with multiple wallets simultaneously
- ⏱️ **Real-time**: Poll drop status until mint goes live

### 🌐 Multi-Marketplace Support
- 🌊 **OpenSea** - FCFS allowlist minting (ETH, Polygon, Base, Arbitrum)
- 🪄 **Magic Eden** - EVM & Solana NFT marketplace
- ⚡ **Tensor** - Solana trading with speed optimization
- 🌫️ **Blur** - Pro trader NFT marketplace
- 🔗 **Direct Mint** - Contract-level minting for any EVM/Solana

### ⚡ Performance Features
- 🔄 **Async Batch**: Concurrent minting across wallets
- 💨 **Pre-sign Cache**: Transactions signed before drop
- 🔗 **Connection Pooling**: Optimized HTTP keep-alive
- ⛽ **Aggressive Gas**: 95th percentile + 20% buffer
- 📊 **Latency Optimization**: Auto-select fastest RPC

## 🚀 Quick Start (GitHub Codespace)

```bash
# 1. Clone & enter repository
cd nft-minter

# 2. Copy environment template
cp .env.template .env

# 3. Edit .env with your private keys and contract addresses
nano .env  # or use VS Code editor

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start minting!
python3 start.py
```

## 📋 Prerequisites

- Python 3.8+
- pip
- GitHub account (for Codespace)
- Wallet with:
  - EVM: Private key (0x format)
  - Solana: Base58 private key or keypair JSON

## 🔧 Configuration

Edit `.env` file with your settings:

```bash
# EVM Chains - Add your private keys and RPC URLs
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
ETH_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
ETH_NFT_CONTRACT=0xCONTRACT_ADDRESS

# Solana
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
SOLANA_PRIVATE_KEY=YOUR_BASE58_KEY
SOLANA_CANDY_MACHINE_ID=YOUR_CM_ID
```

See `.env.template` for all available options.

## 🎮 Usage

### Interactive Mode (Recommended)
```bash
python3 start.py
```

### Quick Mint All Chains
```bash
python3 start.py --quick --all --quantity 1
```

### Mint on Specific Chain
```bash
# EVM Chains: eth, arb, base, polygon, optimism, avax, bsc, linea, scroll
python3 start.py --chain base --quantity 2 --price 0.01

# Solana
python3 start.py --chain sol
```

### Check Wallet Info
```bash
python3 start.py --info
```

## 🌐 Supported Chains

### EVM Layer 1
- ✅ **Ethereum** (Chain ID: 1)
- ✅ **Avalanche** (Chain ID: 43114)
- ✅ **BSC** (Chain ID: 56)

### EVM Layer 2
- ✅ **Arbitrum** (Chain ID: 42161)
- ✅ **Base** (Chain ID: 8453)
- ✅ **Optimism** (Chain ID: 10)
- ✅ **Linea** (Chain ID: 59144)
- ✅ **Scroll** (Chain ID: 534352)
- ✅ **Polygon** (Chain ID: 137)

### Solana
- ✅ **Mainnet**
- ✅ **Candy Machine v3**
- ✅ **Metaplex**

## 🏗️ Architecture

```
nft-minter/
├── config.py          # Configuration loader
├── evm_minter.py      # EVM chains implementation
├── solana_minter.py   # Solana implementation
├── start.py           # Main entry point
├── .env.template      # Environment template
├── .gitignore         # Security: prevents committing secrets
└── requirements.txt   # Python dependencies
```

## 🛡️ Security

- **Private keys stored in `.env`** (never committed)
- **`.env` in `.gitignore`** (automatically excluded from git)
- **No key logging** (keys are never printed or logged)
- **Local-only operation** (no external API for keys)

### Security Checklist
- [ ] `.env` file is in `.gitignore`
- [ ] Never commit `.env` to git
- [ ] Use separate wallet for minting
- [ ] Revoke approvals after minting
- [ ] Monitor wallet for unauthorized transactions

## ⚙️ Advanced Configuration

### Gas Settings
```bash
GAS_LIMIT=300000
MAX_FEE_GWEI=50
PRIORITY_FEE_GWEI=2
GAS_SLIPPAGE=0.1
AGGRESSIVE_GAS=true
GAS_MULTIPLIER=1.2
```

### Retry Configuration
```bash
MAX_RETRIES=3
RETRY_DELAY=1
TX_TIMEOUT=120
CONCURRENT_MINTS=1
```

## 🔗 Block Explorers

After minting, view your transaction:

| Chain | Explorer |
|-------|----------|
| Ethereum | https://etherscan.io/tx/... |
| Arbitrum | https://arbiscan.io/tx/... |
| Base | https://basescan.org/tx/... |
| Polygon | https://polygonscan.com/tx/... |
| Solana | https://solscan.io/tx/... |

## 🐛 Troubleshooting

### "No .env file found"
```bash
cp .env.template .env
# Edit with your keys
```

### "Insufficient funds"
- Check wallet balance with `python3 start.py --info`
- Add native tokens (ETH, SOL, etc.) for gas

### "RPC error"
- Update RPC URL in `.env` with a valid endpoint
- Try Alchemy, Infura, or QuickNode

### "Contract not configured"
- Set NFT contract address in `.env`
- For Solana, set Candy Machine ID

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📜 License

Distributed under MIT License. See `LICENSE` for more information.

## ⚠️ Disclaimer

- **Use at your own risk**
- **Test on testnets first**
- **Never share private keys**
- **Verify contracts before minting**
- **Not responsible for lost funds**

## 📞 Support

- GitHub Issues: [Create an issue](https://github.com/haybarch/nft-minter/issues)
- Discussions: [GitHub Discussions](https://github.com/haybarch/nft-minter/discussions)

---

<p align="center">
  <strong>Built with ❤️ for the NFT community</strong><br>
  <em>Mint fast, mint safe, mint smart 🚀</em>
</p>

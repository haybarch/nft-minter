"""
NFT Minter - Configuration Loader
Loads environment variables and validates configuration
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from rich.console import Console

console = Console()


@dataclass
class EVMChainConfig:
    """Configuration for EVM chain"""
    name: str
    rpc_url: str
    private_key: str
    chain_id: int
    nft_contract: Optional[str] = None
    gas_limit: int = 300000
    max_fee_gwei: int = 50
    priority_fee_gwei: int = 2
    explorer: str = ""


@dataclass
class SolanaConfig:
    """Configuration for Solana"""
    rpc_url: str
    private_key: Optional[str] = None
    keypair_path: Optional[str] = None
    candy_machine_id: Optional[str] = None


@dataclass
class MintConfig:
    """Global minting configuration"""
    concurrent_mints: int = 1
    max_retries: int = 3
    retry_delay: int = 1
    tx_timeout: int = 120
    confirmation_blocks: int = 1
    gas_slippage: float = 0.1
    use_flashbots: bool = False
    aggressive_gas: bool = False
    gas_multiplier: float = 1.2
    log_level: str = "INFO"


class ConfigLoader:
    """Loads and validates configuration from environment"""
    
    # Chain ID mapping
    CHAIN_IDS = {
        "eth": 1,
        "ethereum": 1,
        "arb": 42161,
        "arbitrum": 42161,
        "base": 8453,
        "polygon": 137,
        "matic": 137,
        "optimism": 10,
        "opt": 10,
        "avax": 43114,
        "avalanche": 43114,
        "bsc": 56,
        "bnb": 56,
        "linea": 59144,
        "scroll": 534352,
        "zksync": 324,
        "zora": 7777777,
    }
    
    # Block explorers
    EXPLORERS = {
        "eth": "https://etherscan.io/tx/",
        "arb": "https://arbiscan.io/tx/",
        "base": "https://basescan.org/tx/",
        "polygon": "https://polygonscan.com/tx/",
        "optimism": "https://optimistic.etherscan.io/tx/",
        "avax": "https://snowtrace.io/tx/",
        "bsc": "https://bscscan.com/tx/",
        "linea": "https://lineascan.build/tx/",
        "scroll": "https://scrollscan.com/tx/",
    }
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self._load_env()
        
    def _load_env(self):
        """Load environment variables"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            console.print(f"[green]✓[/green] Loaded configuration from {self.env_file}")
        else:
            console.print(f"[yellow]⚠[/yellow] No {self.env_file} file found, using system environment")
    
    def get_evm_chains(self) -> Dict[str, EVMChainConfig]:
        """Get all configured EVM chains"""
        chains = {}
        
        chain_configs = [
            ("ETH", "eth"),
            ("ARB", "arb"),
            ("BASE", "base"),
            ("POLYGON", "polygon"),
            ("OPTIMISM", "optimism"),
            ("AVAX", "avax"),
            ("BSC", "bsc"),
            ("LINEA", "linea"),
            ("SCROLL", "scroll"),
        ]
        
        for prefix, key in chain_configs:
            rpc_url = os.getenv(f"{prefix}_RPC_URL")
            private_key = os.getenv(f"{prefix}_PRIVATE_KEY")
            
            if rpc_url and private_key:
                nft_contract = os.getenv(f"{prefix}_NFT_CONTRACT")
                chains[key] = EVMChainConfig(
                    name=key,
                    rpc_url=rpc_url,
                    private_key=private_key,
                    chain_id=self.CHAIN_IDS.get(key, 1),
                    nft_contract=nft_contract,
                    gas_limit=int(os.getenv("GAS_LIMIT", 300000)),
                    max_fee_gwei=int(os.getenv("MAX_FEE_GWEI", 50)),
                    priority_fee_gwei=int(os.getenv("PRIORITY_FEE_GWEI", 2)),
                    explorer=self.EXPLORERS.get(key, ""),
                )
        
        return chains
    
    def get_solana_config(self) -> Optional[SolanaConfig]:
        """Get Solana configuration"""
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        private_key = os.getenv("SOLANA_PRIVATE_KEY")
        keypair_path = os.getenv("SOLANA_KEYPAIR_PATH")
        candy_machine_id = os.getenv("SOLANA_CANDY_MACHINE_ID")
        
        if private_key or keypair_path:
            return SolanaConfig(
                rpc_url=rpc_url,
                private_key=private_key,
                keypair_path=keypair_path,
                candy_machine_id=candy_machine_id,
            )
        return None
    
    def get_mint_config(self) -> MintConfig:
        """Get global minting configuration"""
        return MintConfig(
            concurrent_mints=int(os.getenv("CONCURRENT_MINTS", 1)),
            max_retries=int(os.getenv("MAX_RETRIES", 3)),
            retry_delay=int(os.getenv("RETRY_DELAY", 1)),
            tx_timeout=int(os.getenv("TX_TIMEOUT", 120)),
            confirmation_blocks=int(os.getenv("CONFIRMATION_BLOCKS", 1)),
            gas_slippage=float(os.getenv("GAS_SLIPPAGE", 0.1)),
            use_flashbots=os.getenv("USE_FLASHBOTS", "false").lower() == "true",
            aggressive_gas=os.getenv("AGGRESSIVE_GAS", "false").lower() == "true",
            gas_multiplier=float(os.getenv("GAS_MULTIPLIER", 1.2)),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check at least one chain is configured
        evm_chains = self.get_evm_chains()
        solana = self.get_solana_config()
        
        if not evm_chains and not solana:
            errors.append("No chains configured! Please set at least one chain in .env")
        
        # Validate EVM private keys format
        for name, config in evm_chains.items():
            if not config.private_key.startswith("0x"):
                errors.append(f"{name}: Private key must start with 0x")
        
        if errors:
            console.print("[red]✗ Configuration errors:[/red]")
            for error in errors:
                console.print(f"  [red]- {error}[/red]")
            return False
        
        console.print(f"[green]✓[/green] Configured {len(evm_chains)} EVM chain(s)")
        if solana:
            console.print("[green]✓[/green] Solana configured")
        
        return True
    
    def print_summary(self):
        """Print configuration summary"""
        evm_chains = self.get_evm_chains()
        solana = self.get_solana_config()
        mint_config = self.get_mint_config()
        
        console.print("\n[bold cyan]Configuration Summary[/bold cyan]")
        console.print("=" * 50)
        
        console.print(f"\n[bold]EVM Chains ({len(evm_chains)}):[/bold]")
        for name, config in evm_chains.items():
            status = "✓" if config.nft_contract else "⚠ (no contract)"
            console.print(f"  {status} {name.upper()} (Chain ID: {config.chain_id})")
        
        if solana:
            console.print(f"\n[bold]Solana:[/bold]")
            console.print(f"  ✓ RPC: {solana.rpc_url[:40]}...")
        
        console.print(f"\n[bold]Minting Settings:[/bold]")
        console.print(f"  Max Retries: {mint_config.max_retries}")
        console.print(f"  TX Timeout: {mint_config.tx_timeout}s")
        console.print(f"  Concurrent: {mint_config.concurrent_mints}")
        console.print("=" * 50)

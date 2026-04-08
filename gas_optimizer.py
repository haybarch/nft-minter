#!/usr/bin/env python3
"""
Smart Gas Optimizer - L2 Optimized Gas Calculator
Auto-calculate optimal gas for Layer 2 chains (Base, Arbitrum, Polygon)
Balanced between cost and speed
"""

import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class GasStrategy(Enum):
    """Gas pricing strategies"""
    ECONOMY = "economy"      # Minimum gas, slower
    BALANCED = "balanced"    # Optimal cost/speed (RECOMMENDED)
    AGGRESSIVE = "aggressive"  # High gas, fastest


@dataclass
class GasConfig:
    """Gas configuration for a chain"""
    chain: str
    strategy: GasStrategy
    max_fee_gwei: float
    priority_fee_gwei: float
    gas_limit: int
    is_l2: bool = False


class SmartGasOptimizer:
    """
    Smart gas optimizer untuk L2 chains
    Optimized untuk Base, Arbitrum, Polygon (murah)
    """
    
    # Chain type mapping
    L2_CHAINS = ["base", "arbitrum", "arb", "polygon", "optimism", "op", "zksync", "linea", "scroll"]
    L1_CHAINS = ["eth", "ethereum", "bsc", "avalanche", "avax"]
    
    # Default gas config per chain (dari .env atau fallback)
    DEFAULT_CONFIGS = {
        # L2 Chains - Ultra murah
        "base": {
            "strategy": "balanced",
            "max_fee_gwei": 1.0,          # 1 gwei max
            "priority_fee_gwei": 0.1,    # 0.1 gwei priority
            "gas_limit": 300000,
            "is_l2": True,
        },
        "arbitrum": {
            "strategy": "balanced",
            "max_fee_gwei": 2.0,
            "priority_fee_gwei": 0.5,
            "gas_limit": 300000,
            "is_l2": True,
        },
        "polygon": {
            "strategy": "balanced",
            "max_fee_gwei": 50.0,         # Polygon model berbeda
            "priority_fee_gwei": 30.0,
            "gas_limit": 300000,
            "is_l2": True,
        },
        "optimism": {
            "strategy": "balanced",
            "max_fee_gwei": 1.0,
            "priority_fee_gwei": 0.1,
            "gas_limit": 300000,
            "is_l2": True,
        },
        # L1 Chains - Lebih mahal
        "eth": {
            "strategy": "balanced",
            "max_fee_gwei": 50.0,
            "priority_fee_gwei": 2.0,
            "gas_limit": 300000,
            "is_l2": False,
        },
        "bsc": {
            "strategy": "balanced",
            "max_fee_gwei": 5.0,
            "priority_fee_gwei": 1.0,
            "gas_limit": 300000,
            "is_l2": False,
        },
        "avalanche": {
            "strategy": "balanced",
            "max_fee_gwei": 50.0,
            "priority_fee_gwei": 2.0,
            "gas_limit": 300000,
            "is_l2": False,
        },
    }
    
    def __init__(self, chain: str = "base"):
        self.chain = chain.lower()
        self.config = self._load_config()
    
    def _load_config(self) -> GasConfig:
        """Load gas config from environment or defaults"""
        chain_upper = self.chain.upper()
        
        # Get from environment
        strategy_str = os.getenv(
            f"{chain_upper}_GAS_STRATEGY",
            os.getenv("DEFAULT_GAS_STRATEGY", "balanced")
        )
        
        max_fee = float(os.getenv(
            f"{chain_upper}_MAX_FEE_GWEI",
            self.DEFAULT_CONFIGS.get(self.chain, {}).get("max_fee_gwei", 50.0)
        ))
        
        priority_fee = float(os.getenv(
            f"{chain_upper}_PRIORITY_FEE_GWEI",
            self.DEFAULT_CONFIGS.get(self.chain, {}).get("priority_fee_gwei", 2.0)
        ))
        
        gas_limit = int(os.getenv(
            f"{chain_upper}_GAS_LIMIT",
            self.DEFAULT_CONFIGS.get(self.chain, {}).get("gas_limit", 300000)
        ))
        
        is_l2 = self.chain in self.L2_CHAINS
        
        return GasConfig(
            chain=self.chain,
            strategy=GasStrategy(strategy_str),
            max_fee_gwei=max_fee,
            priority_fee_gwei=priority_fee,
            gas_limit=gas_limit,
            is_l2=is_l2,
        )
    
    def calculate_gas(self, network_congestion: float = 1.0) -> Tuple[int, int]:
        """
        Calculate optimal gas prices
        
        Args:
            network_congestion: 1.0 = normal, >1.0 = congested
        
        Returns:
            (max_fee_per_gas, priority_fee_per_gas) in wei
        """
        from web3 import Web3
        
        config = self.config
        
        # Apply strategy multiplier
        if config.strategy == GasStrategy.ECONOMY:
            multiplier = 0.8
        elif config.strategy == GasStrategy.AGGRESSIVE:
            multiplier = 1.5
        else:  # BALANCED
            multiplier = 1.0
        
        # Apply congestion multiplier
        total_multiplier = multiplier * network_congestion
        
        # Calculate final gas prices
        max_fee = config.max_fee_gwei * total_multiplier
        priority_fee = config.priority_fee_gwei * total_multiplier
        
        # Ensure minimum for L2
        if config.is_l2:
            priority_fee = max(priority_fee, 0.05)  # Minimum 0.05 gwei untuk L2
        
        # Convert to wei
        max_fee_wei = Web3.to_wei(max_fee, 'gwei')
        priority_fee_wei = Web3.to_wei(priority_fee, 'gwei')
        
        return max_fee_wei, priority_fee_wei
    
    def estimate_cost(self, gas_used: int = 150000) -> Dict[str, float]:
        """
        Estimate minting cost in native token
        
        Args:
            gas_used: Estimated gas consumption
        
        Returns:
            Cost breakdown
        """
        max_fee_wei, priority_fee_wei = self.calculate_gas()
        
        # Effective gas price (base fee + priority)
        effective_gas_price = min(max_fee_wei, priority_fee_wei + max_fee_wei // 2)
        
        # Total cost in wei
        total_wei = gas_used * effective_gas_price
        
        # Convert to ETH/native
        total_eth = total_wei / 1e18
        
        return {
            "gas_used": gas_used,
            "max_fee_gwei": max_fee_wei / 1e9,
            "priority_fee_gwei": priority_fee_wei / 1e9,
            "total_eth": total_eth,
            "chain": self.chain,
            "is_l2": self.config.is_l2,
        }
    
    def get_recommendation(self) -> str:
        """Get human-readable recommendation"""
        cost = self.estimate_cost()
        
        if self.config.is_l2:
            return (
                f"[green]✓ L2 Optimized ({self.chain.upper()})[/green]\n"
                f"  Max Fee: {cost['max_fee_gwei']:.2f} gwei\n"
                f"  Priority: {cost['priority_fee_gwei']:.2f} gwei\n"
                f"  Est. Cost: ~${cost['total_eth']:.4f} ETH (${cost['total_eth'] * 3000:.2f})\n"
                f"  [dim]L2 gas sangat murah! Recommended untuk frequent minting.[/dim]"
            )
        else:
            return (
                f"[yellow]⚠ L1 ({self.chain.upper()}) - Lebih mahal[/yellow]\n"
                f"  Max Fee: {cost['max_fee_gwei']:.2f} gwei\n"
                f"  Priority: {cost['priority_fee_gwei']:.2f} gwei\n"
                f"  Est. Cost: ~${cost['total_eth']:.4f} ETH (${cost['total_eth'] * 3000:.2f})\n"
                f"  [dim]Consider using L2 (Base/Arbitrum) untuk hemat gas.[/dim]"
            )
    
    def set_strategy(self, strategy: str):
        """Change gas strategy dynamically"""
        try:
            self.config.strategy = GasStrategy(strategy.lower())
        except ValueError:
            console.print(f"[red]Invalid strategy: {strategy}[/red]")
    
    @staticmethod
    def compare_chains() -> None:
        """Compare gas costs across all supported chains"""
        table = Table(
            title="⛽ Gas Cost Comparison (Est. 150k gas)",
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Chain", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Max Fee", justify="right")
        table.add_column("Priority", justify="right")
        table.add_column("Est. Cost", justify="right")
        table.add_column("Recommendation", style="dim")
        
        chains = ["base", "arbitrum", "polygon", "optimism", "eth", "bsc"]
        
        for chain in chains:
            opt = SmartGasOptimizer(chain)
            cost = opt.estimate_cost(150000)
            
            chain_type = "L2" if opt.config.is_l2 else "L1"
            
            if opt.config.is_l2:
                rec = "✅ Ultra murah"
                cost_color = "green"
            elif chain == "eth":
                rec = "⚠️ Mahal"
                cost_color = "red"
            else:
                rec = "🟡 Moderate"
                cost_color = "yellow"
            
            table.add_row(
                chain.upper(),
                chain_type,
                f"{cost['max_fee_gwei']:.2f} gwei",
                f"{cost['priority_fee_gwei']:.2f} gwei",
                f"[{cost_color}]{cost['total_eth']:.6f} ETH[/{cost_color}]",
                rec
            )
        
        console.print(table)
        console.print("\n[bold green]💡 Recommendation: Gunakan L2 (Base/Arbitrum) untuk minting reguler[/bold green]")


def get_optimal_gas(chain: str, strategy: str = "balanced") -> Dict[str, int]:
    """
    Quick function to get optimal gas for a chain
    
    Returns dict with maxFeePerGas and maxPriorityFeePerGas in wei
    """
    optimizer = SmartGasOptimizer(chain)
    optimizer.set_strategy(strategy)
    
    max_fee, priority_fee = optimizer.calculate_gas()
    
    return {
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
        "gasLimit": optimizer.config.gas_limit,
    }


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Gas Optimizer")
    parser.add_argument("--compare", "-c", action="store_true", help="Compare all chains")
    parser.add_argument("--chain", default="base", help="Chain to optimize for")
    parser.add_argument("--strategy", "-s", default="balanced", 
                       choices=["economy", "balanced", "aggressive"])
    
    args = parser.parse_args()
    
    if args.compare:
        SmartGasOptimizer.compare_chains()
    else:
        opt = SmartGasOptimizer(args.chain)
        opt.set_strategy(args.strategy)
        
        console.print(Panel.fit(
            f"[bold cyan]Smart Gas Optimizer: {args.chain.upper()}[/bold cyan]\n"
            f"Strategy: {args.strategy.upper()}",
            border_style="cyan"
        ))
        
        console.print(opt.get_recommendation())
        
        cost = opt.estimate_cost()
        console.print(f"\n[bold]Transaction Config:[/bold]")
        console.print(f"  maxFeePerGas: {cost['max_fee_gwei']:.3f} gwei")
        console.print(f"  maxPriorityFeePerGas: {cost['priority_fee_gwei']:.3f} gwei")
        console.print(f"  gasLimit: {opt.config.gas_limit}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NFT Minter - Super Fast Multi-Chain NFT Minting
Start command: python3 start.py

Supports:
- EVM Chains: Ethereum, Arbitrum, Base, Polygon, Optimism, Avalanche, BSC, Linea, Scroll
- Solana: Candy Machine v3, Metaplex

Setup:
1. Copy .env.template to .env
2. Fill in your private keys and RPC URLs
3. Update NFT contract addresses
4. Run: python3 start.py
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from colorama import init as colorama_init

from config import ConfigLoader, EVMChainConfig, SolanaConfig
from evm_minter import EVMMinter, MintResult
from solana_minter import SolanaMinter, SolanaMintResult

colorama_init()
console = Console()


def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   🚀 NFT MINTER - Super Fast Multi-Chain Minting          ║
    ║                                                           ║
    ║   EVM: ETH | ARB | BASE | POLYGON | OP | AVAX | BSC       ║
    ║   SOLANA: Candy Machine v3 | Metaplex                     ║
    ║                                                           ║
    ║   Mode: Codespace Ready | One-Command Start               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def check_environment():
    """Check if running in GitHub Codespace and configure accordingly"""
    codespace_name = os.getenv("CODESPACE_NAME")
    github_token = os.getenv("GITHUB_TOKEN")
    
    if codespace_name:
        console.print(f"[green]✓[/green] Running in GitHub Codespace: {codespace_name}")
        
        # Auto-configure common Codespace paths
        solana_keypair_path = os.path.expanduser("~/.config/solana/id.json")
        if os.path.exists(solana_keypair_path):
            if not os.getenv("SOLANA_KEYPAIR_PATH"):
                os.environ["SOLANA_KEYPAIR_PATH"] = solana_keypair_path
                console.print(f"[green]✓[/green] Auto-detected Solana keypair")
        
        return True
    
    return False


def setup_environment():
    """Setup environment and check .env file"""
    if not os.path.exists(".env"):
        console.print("[yellow]⚠ .env file not found![/yellow]")
        
        if os.path.exists(".env.template"):
            console.print("\n[bold]To get started:[/bold]")
            console.print("  1. Copy .env.template to .env")
            console.print("  2. Fill in your private keys and contract addresses")
            console.print("  3. Run this script again\n")
            console.print("  Command: cp .env.template .env")
        else:
            console.print("[red]✗ .env.template also missing! Please reclone the repository.[/red]")
        
        sys.exit(1)


def mint_evm_chain(config: EVMChainConfig, quantity: int = 1, price: Optional[float] = None) -> MintResult:
    """Mint on a single EVM chain"""
    minter = EVMMinter(config)
    
    # Show balance
    balance = minter.get_balance()
    console.print(f"  Balance: {balance:.4f} ETH (or native token)")
    
    if config.nft_contract:
        info = minter.get_contract_info()
        if info:
            console.print(f"  Contract info: {info}")
    
    # Execute mint
    return minter.mint(quantity=quantity, mint_price_eth=price)


def mint_solana(config: SolanaConfig, candy_machine_id: Optional[str] = None) -> SolanaMintResult:
    """Mint on Solana"""
    minter = SolanaMinter(config)
    
    # Show balance
    balance = minter.get_balance()
    console.print(f"  Balance: {balance:.4f} SOL")
    
    # Execute mint
    return minter.mint_candy_machine(candy_machine_id)


def interactive_mode(config_loader: ConfigLoader):
    """Interactive minting mode"""
    console.print("\n[bold cyan]Interactive Minting Mode[/bold cyan]\n")
    
    # Get available chains
    evm_chains = config_loader.get_evm_chains()
    solana = config_loader.get_solana_config()
    
    # Build options
    options = []
    
    for name, chain in evm_chains.items():
        contract_status = "✓" if chain.nft_contract else "⚠"
        options.append((name.upper(), f"EVM - {name.upper()} {contract_status}", chain))
    
    if solana:
        cm_status = "✓" if solana.candy_machine_id else "⚠"
        options.append(("SOL", f"Solana {cm_status}", solana))
    
    if not options:
        console.print("[red]✗ No chains configured![/red]")
        return
    
    # Show menu
    console.print("[bold]Available chains:[/bold]")
    for i, (key, label, _) in enumerate(options, 1):
        console.print(f"  {i}. {label}")
    console.print(f"  {len(options) + 1}. Exit")
    
    # Get selection
    try:
        choice = int(console.input("\nSelect chain (number): ")) - 1
        
        if choice == len(options):
            return
        
        if choice < 0 or choice >= len(options):
            console.print("[red]Invalid selection[/red]")
            return
        
        _, label, config = options[choice]
        
        # Get mint parameters
        quantity = int(console.input("Quantity to mint [1]: ") or "1")
        
        if "EVM" in label:
            price = console.input("Mint price in ETH (or 0 for free) [0]: ") or "0"
            price_float = float(price)
            
            # Execute
            result = mint_evm_chain(config, quantity, price_float)
            
            if result.success:
                console.print(f"\n[green]✓ Successfully minted on {label}![/green]")
            else:
                console.print(f"\n[red]✗ Mint failed: {result.error}[/red]")
        
        else:  # Solana
            cm_id = console.input(f"Candy Machine ID [{config.candy_machine_id or 'none'}]: ")
            cm_id = cm_id or config.candy_machine_id
            
            result = mint_solana(config, cm_id)
            
            if result.success:
                console.print(f"\n[green]✓ Successfully minted on Solana![/green]")
            else:
                console.print(f"\n[red]✗ Mint failed: {result.error}[/red]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


def quick_mint_all(config_loader: ConfigLoader, quantity: int = 1):
    """Quick mint on all configured chains"""
    console.print("\n[bold cyan]Quick Mint Mode - All Chains[/bold cyan]\n")
    
    evm_chains = config_loader.get_evm_chains()
    solana = config_loader.get_solana_config()
    
    results = []
    
    # Mint on EVM chains
    for name, chain in evm_chains.items():
        if chain.nft_contract:
            console.print(f"\n[bold]{name.upper()}[/bold]")
            result = mint_evm_chain(chain, quantity)
            results.append((name.upper(), result))
        else:
            console.print(f"[dim]⚠ Skipping {name.upper()} - no contract configured[/dim]")
    
    # Mint on Solana
    if solana and solana.candy_machine_id:
        console.print(f"\n[bold]SOLANA[/bold]")
        result = mint_solana(solana)
        results.append(("SOLANA", result))
    else:
        console.print(f"[dim]⚠ Skipping Solana - no Candy Machine configured[/dim]")
    
    # Print summary
    console.print("\n" + "=" * 50)
    console.print("[bold]Mint Summary:[/bold]")
    
    success_count = sum(1 for _, r in results if r.success)
    
    for chain, result in results:
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        console.print(f"  {status} {chain}: {result.tx_hash or result.signature or result.error}")
    
    console.print(f"\nTotal: {success_count}/{len(results)} successful")


def print_wallet_info(config_loader: ConfigLoader):
    """Print wallet information for all chains"""
    console.print("\n[bold cyan]Wallet Information[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Chain")
    table.add_column("Address")
    table.add_column("Balance")
    
    evm_chains = config_loader.get_evm_chains()
    solana = config_loader.get_solana_config()
    
    # EVM wallets
    for name, chain in evm_chains.items():
        try:
            from web3 import Web3
            w3 = Web3()
            account = w3.eth.account.from_key(chain.private_key)
            address = account.address
            
            # Get balance
            w3 = Web3(Web3.HTTPProvider(chain.rpc_url))
            balance = w3.eth.get_balance(address)
            balance_eth = Web3.from_wei(balance, 'ether')
            
            symbol = "ETH" if name == "eth" else name.upper()
            table.add_row(name.upper(), address[:20] + "...", f"{balance_eth:.4f} {symbol}")
        except Exception as e:
            table.add_row(name.upper(), "Error", str(e)[:30])
    
    # Solana wallet
    if solana:
        try:
            minter = SolanaMinter(solana)
            balance = minter.get_balance()
            table.add_row("SOLANA", minter.wallet_address[:20] + "...", f"{balance:.4f} SOL")
        except Exception as e:
            table.add_row("SOLANA", "Error", str(e)[:30])
    
    console.print(table)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="NFT Minter - Super Fast Multi-Chain Minting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 start.py                    # Interactive mode
  python3 start.py --quick --all      # Mint on all configured chains
  python3 start.py --info             # Show wallet info only
  python3 start.py --chain base       # Mint only on Base
        """
    )
    
    parser.add_argument("--quick", "-q", action="store_true", help="Quick mint mode (no prompts)")
    parser.add_argument("--all", "-a", action="store_true", help="Mint on all configured chains")
    parser.add_argument("--info", "-i", action="store_true", help="Show wallet information only")
    parser.add_argument("--chain", "-c", type=str, help="Mint on specific chain only")
    parser.add_argument("--quantity", "-n", type=int, default=1, help="Quantity to mint")
    parser.add_argument("--price", "-p", type=float, help="Mint price (for EVM chains)")
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Check environment
    is_codespace = check_environment()
    
    # Setup and validate
    setup_environment()
    
    # Load config
    config_loader = ConfigLoader(".env")
    
    if not config_loader.validate():
        sys.exit(1)
    
    # Print config summary
    config_loader.print_summary()
    
    # Handle modes
    if args.info:
        print_wallet_info(config_loader)
        return
    
    if args.quick and args.all:
        quick_mint_all(config_loader, args.quantity)
        return
    
    if args.chain:
        # Mint on specific chain
        evm_chains = config_loader.get_evm_chains()
        solana = config_loader.get_solana_config()
        
        chain_key = args.chain.lower()
        
        if chain_key in evm_chains:
            console.print(f"\n[bold cyan]Minting on {chain_key.upper()}[/bold cyan]\n")
            result = mint_evm_chain(evm_chains[chain_key], args.quantity, args.price)
            
            if result.success:
                console.print(f"\n[green]✓ Mint successful![/green]")
                if result.explorer_url:
                    console.print(f"  {result.explorer_url}")
            else:
                console.print(f"\n[red]✗ Mint failed: {result.error}[/red]")
        
        elif chain_key in ["sol", "solana"] and solana:
            console.print(f"\n[bold cyan]Minting on Solana[/bold cyan]\n")
            result = mint_solana(solana)
            
            if result.success:
                console.print(f"\n[green]✓ Mint successful![/green]")
                if result.explorer_url:
                    console.print(f"  {result.explorer_url}")
            else:
                console.print(f"\n[red]✗ Mint failed: {result.error}[/red]")
        
        else:
            console.print(f"[red]Chain '{args.chain}' not configured[/red]")
        
        return
    
    # Default: interactive mode
    interactive_mode(config_loader)


if __name__ == "__main__":
    main()

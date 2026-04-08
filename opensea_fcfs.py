#!/usr/bin/env python3
"""
OpenSea FCFS Minter - Standalone Script for Competitive Minting
Ultra-fast minting for First Come First Serve drops

Usage:
    python3 opensea_fcfs.py --chain base --contract 0x... --poll
    python3 opensea_fcfs.py --chain eth --contract 0x... --prewarm
    python3 opensea_fcfs.py --chain polygon --contract 0x... --multi-wallet
"""

import asyncio
import argparse
import os
import sys
from typing import List

from opensea_minter import (
    OpenSeaFCFSMinter, OpenSeaConfig, OpenSeaMintResult,
    create_opensea_config_from_env, MultiWalletOpenSeaMinter
)
from speed_optimized import AsyncBatchMinter, SpeedConfig
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from dotenv import load_dotenv

load_dotenv()
console = Console()


def print_banner():
    """Print FCFS banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ⚡ OPENSEA FCFS MINTER - Ultra Competitive            ║
    ║                                                           ║
    ║   First Come First Serve Speed Demon                      ║
    ║   Based on reverse engineered GraphQL API                 ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold bright_yellow")


def get_multi_wallet_configs(chain: str) -> List[OpenSeaConfig]:
    """Get multiple wallet configs from FCFS_WALLET_KEYS"""
    wallet_keys = os.getenv("FCFS_WALLET_KEYS", "")
    if not wallet_keys:
        # Fallback to single wallet
        config = create_opensea_config_from_env(chain)
        return [config] if config else []
    
    rpc_url = os.getenv(f"{chain.upper()}_RPC_URL")
    configs = []
    
    for key in wallet_keys.split(","):
        key = key.strip()
        if key:
            configs.append(OpenSeaConfig(
                chain=chain.lower(),
                rpc_url=rpc_url,
                private_key=key,
            ))
    
    return configs


async def prewarm_and_snipe(
    chain: str,
    contract_address: str,
    token_id: str,
    quantity: str,
):
    """Prewarm calldata then snipe when drop is live"""
    console.print(f"\n[bold yellow]FCFS Mode: Prewarm & Snipe[/bold yellow]")
    console.print(f"Chain: {chain.upper()}")
    console.print(f"Contract: {contract_address}")
    console.print(f"Token ID: {token_id}")
    console.print(f"Quantity: {quantity}\n")
    
    # Get configs
    configs = get_multi_wallet_configs(chain)
    if not configs:
        console.print("[red]✗ No wallet configurations found![/red]")
        console.print("Set FCFS_WALLET_KEYS or {CHAIN}_PRIVATE_KEY in .env")
        return
    
    console.print(f"[green]✓ Loaded {len(configs)} wallet(s)[/green]\n")
    
    # Initialize batch minter
    speed_config = SpeedConfig(
        aggressive_gas=True,
        request_timeout=3.0,
    )
    batch_minter = AsyncBatchMinter(speed_config)
    
    # Prewarm phase
    console.print("[bold]Phase 1: Prewarming...[/bold]")
    
    primary_minter = OpenSeaFCFSMinter(configs[0])
    await primary_minter.graphql.init_session()
    
    poll_interval = float(os.getenv("FCFS_POLL_INTERVAL", "0.5"))
    
    calldata = await primary_minter.prewarm_calldata(
        contract_address,
        token_id,
        quantity,
        interval=poll_interval,
    )
    
    if not calldata:
        console.print("[red]✗ Failed to get calldata[/red]")
        return
    
    # Snipe phase
    console.print("\n[bold]Phase 2: SNIPING! [/bold] ⚡⚡⚡\n")
    
    if len(configs) > 1:
        # Multi-wallet snipe
        multi_minter = MultiWalletOpenSeaMinter(configs)
        results = await multi_minter.snipe_with_all(
            contract_address, token_id, quantity
        )
        await multi_minter.close()
    else:
        # Single wallet
        result = await primary_minter.snipe_mint(
            contract_address, token_id, quantity
        )
        results = [(configs[0].wallet_address[:10], result)]
    
    await primary_minter.close()
    await batch_minter.close()
    
    # Print results
    print_results(results)


def print_results(results: List):
    """Print mint results table"""
    table = Table(
        title="FCFS Mint Results",
        box=box.ROUNDED,
        header_style="bold magenta"
    )
    
    table.add_column("Wallet", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Time (ms)", justify="right")
    table.add_column("TX Hash", style="dim")
    table.add_column("Link", style="blue")
    
    for wallet, result in results:
        status = "✅ Success" if result.success else "❌ Failed"
        status_style = "green" if result.success else "red"
        
        time_str = f"{result.elapsed_ms:.1f}" if result.elapsed_ms else "N/A"
        tx_short = result.tx_hash[:15] + "..." if result.tx_hash else "N/A"
        
        table.add_row(
            wallet,
            f"[{status_style}]{status}[/{status_style}]",
            time_str,
            tx_short,
            result.explorer_url or "N/A"
        )
    
    console.print(table)
    
    # Summary
    success_count = sum(1 for _, r in results if r.success)
    total = len(results)
    
    console.print(f"\n[bold]Summary:[/bold] {success_count}/{total} successful")
    
    if success_count > 0:
        avg_time = sum(r.elapsed_ms for _, r in results if r.success) / success_count
        console.print(f"[bold]Avg Time:[/bold] {avg_time:.1f}ms")


async def poll_drop_status(chain: str, contract_address: str):
    """Poll drop status until live"""
    config = create_opensea_config_from_env(chain)
    if not config:
        console.print("[red]✗ No configuration found![/red]")
        return
    
    minter = OpenSeaFCFSMinter(config)
    await minter.graphql.init_session()
    
    console.print(f"\n[yellow]Polling drop status for {contract_address}...[/yellow]")
    console.print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            status = await minter.graphql.check_drop_status(contract_address)
            
            if "error" in status:
                console.print(f"[red]Error: {status['error']}[/red]")
            else:
                console.print(f"[dim]{status}[/dim]")
            
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped polling[/yellow]")
    finally:
        await minter.close()


async def speed_test(chain: str):
    """Test minting speed (simulation mode)"""
    console.print("\n[bold cyan]Speed Test Mode[/bold cyan]\n")
    
    from speed_optimized import benchmark_mint_speed
    
    config = create_opensea_config_from_env(chain)
    if not config:
        console.print("[red]✗ No configuration![/red]")
        return
    
    results = await benchmark_mint_speed([config], "0x...", iterations=5)
    
    console.print(f"[bold]Results:[/bold]")
    console.print(f"  Average: {results['avg_ms']:.2f}ms")
    console.print(f"  Min: {results['min_ms']:.2f}ms")
    console.print(f"  Max: {results['max_ms']:.2f}ms")


def main():
    parser = argparse.ArgumentParser(
        description="OpenSea FCFS Minter - Competitive Drop Sniping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 opensea_fcfs.py --chain base --contract 0x123... --poll
  python3 opensea_fcfs.py --chain eth --contract 0x456... --prewarm
  python3 opensea_fcfs.py --chain polygon --contract 0x789... --multi-wallet
  python3 opensea_fcfs.py --chain base --test-speed
        """
    )
    
    parser.add_argument("--chain", "-c", required=True,
                       choices=["eth", "polygon", "base", "arb", "optimism"],
                       help="Chain to mint on")
    parser.add_argument("--contract", "-a",
                       help="NFT contract address")
    parser.add_argument("--token-id", "-t", default="0",
                       help="Token ID to mint (default: 0)")
    parser.add_argument("--quantity", "-q", default="1",
                       help="Quantity to mint (default: 1)")
    
    parser.add_argument("--prewarm", "-p", action="store_true",
                       help="Prewarm calldata until drop is live")
    parser.add_argument("--poll", action="store_true",
                       help="Poll drop status only")
    parser.add_argument("--multi-wallet", "-m", action="store_true",
                       help="Use multiple wallets from FCFS_WALLET_KEYS")
    parser.add_argument("--test-speed", action="store_true",
                       help="Test minting speed (simulation)")
    
    args = parser.parse_args()
    
    print_banner()
    
    # Validate
    if not args.contract and not args.test_speed:
        console.print("[red]✗ Contract address required![/red]")
        parser.print_help()
        sys.exit(1)
    
    # Execute
    try:
        if args.poll:
            asyncio.run(poll_drop_status(args.chain, args.contract))
        elif args.test_speed:
            asyncio.run(speed_test(args.chain))
        else:
            asyncio.run(prewarm_and_snipe(
                args.chain,
                args.contract,
                args.token_id,
                args.quantity,
            ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NFT Minter Bot v3.1 - Main Entry Point
Multi-Wallet + Smart Gas + Auto Contract Detection
"""

import os
import sys
import asyncio
import subprocess
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt, IntPrompt
from rich.align import Align

# Import our modules
from wallet_manager import WalletManager, Wallet, select_wallet_interactive
from gas_optimizer import SmartGasOptimizer, get_optimal_gas

console = Console()


def print_banner():
    """Print main banner"""
    banner_text = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🚀 NFT MINTER BOT v3.1 - Multi-Wallet Edition         ║
║                                                           ║
║   Multi-Wallet • Smart Gas • Auto Contract Detection      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner_text, style="bold bright_cyan", border_style="cyan"))


def print_wallet_info():
    """Display wallet information from wallet manager"""
    manager = WalletManager()
    manager.display_wallets()


def main_menu():
    """Display main menu"""
    console.print("\n[bold yellow]⚡ MAIN MENU[/bold yellow]\n")
    
    options = [
        ("1", "🎯 OpenSea FCFS Specialist", "Ultra-fast competitive minting (allowlist)"),
        ("2", "🔥 Public Mint Auto", "Auto-mint public drops (no allowlist needed)"),
        ("3", "📡 Scan Public Mints", "Monitor upcoming public mints"),
        ("4", "🔗 Direct Contract Mint", "Mint directly to smart contracts"),
        ("5", "💼 Select Wallet", "Choose wallet for minting"),
        ("6", "⛽ Smart Gas", "Check gas optimization"),
        ("7", "💰 Check Wallet Balances", "View all wallet balances"),
        ("8", "🔐 Setup OpenSea Auth", "Auto-fetch auth tokens"),
        ("9", "⚙️  Settings", "Configure RPC, gas, wallets"),
        ("10", "❓ Help & Info", "Documentation and examples"),
        ("0", "🚪 Exit", "Close the bot"),
    ]
    
    table = Table(show_header=False, box=box.SIMPLE)
    table.add_column("#", style="bold bright_cyan", justify="center")
    table.add_column("Option", style="bright_white")
    table.add_column("Description", style="dim")
    
    for num, option, desc in options:
        table.add_row(num, option, desc)
    
    console.print(table)
    
    return IntPrompt.ask("\n[bold cyan]Select option[/bold cyan]", choices=[str(i) for i in range(11)])


def opensea_fcfs_menu():
    """OpenSea FCFS submenu"""
    console.print("\n[bold yellow]🎯 OPENSEA FCFS SPECIALIST[/bold yellow]\n")
    
    # Check if auth is configured
    has_auth = bool(os.getenv("OPENSEA_AUTH_TOKEN"))
    
    if not has_auth:
        console.print("[red]⚠️  OpenSea auth not configured![/red]")
        console.print("Run option 4 first: Setup OpenSea Auth\n")
        return
    
    chain = Prompt.ask(
        "Select chain",
        choices=["base", "eth", "polygon", "arb", "optimism"],
        default="base"
    )
    
    contract = Prompt.ask("NFT Contract Address")
    
    if not contract.startswith("0x"):
        console.print("[red]❌ Invalid contract address[/red]")
        return
    
    mode = Prompt.ask(
        "Mode",
        choices=["prewarm", "quick", "multi"],
        default="prewarm"
    )
    
    # Build command
    cmd = ["python3", "opensea_fcfs.py", "--chain", chain, "--contract", contract]
    
    if mode == "prewarm":
        cmd.append("--prewarm")
    elif mode == "multi":
        cmd.append("--multi-wallet")
    
    console.print(f"\n[bold cyan]Executing:[/bold cyan] {' '.join(cmd)}\n")
    
    # Run
    subprocess.run(cmd)


def direct_mint_menu():
    """Direct mint submenu"""
    console.print("\n[bold yellow]🔗 DIRECT CONTRACT MINT[/bold yellow]\n")
    
    chain = Prompt.ask(
        "Select chain",
        choices=["eth", "base", "arb", "polygon", "optimism", "avax", "bsc", "linea", "scroll", "sol"],
        default="base"
    )
    
    contract = Prompt.ask("Contract Address (press Enter to skip for general mint)", default="")
    
    quantity = IntPrompt.ask("Quantity", default=1)
    
    # Build command
    cmd = ["python3", "start.py", "--chain", chain, "--quantity", str(quantity)]
    
    if contract:
        cmd.extend(["--contract", contract])
    
    console.print(f"\n[bold cyan]Executing:[/bold cyan] {' '.join(cmd)}\n")
    
    subprocess.run(cmd)


def check_balances():
    """Check all wallet balances"""
    console.print("\n[bold yellow]💰 CHECKING WALLET BALANCES[/bold yellow]\n")
    
    subprocess.run(["python3", "start.py", "--info"])


def setup_opensea_auth():
    """Setup OpenSea authentication"""
    console.print("\n[bold yellow]🔐 OPENSEA AUTH SETUP[/bold yellow]\n")
    
    console.print("[dim]This will attempt to fetch OpenSea auth tokens...[/dim]\n")
    
    method = Prompt.ask(
        "Method",
        choices=["manual", "auto"],
        default="manual"
    )
    
    if method == "auto":
        console.print("\n[yellow]⚠️  Auto-auth requires browser automation[/yellow]")
        console.print("Make sure you have valid credentials in .env\n")
        subprocess.run(["python3", "auto_auth.py"])
    else:
        console.print("\n[bold cyan]Manual Setup Instructions:[/bold cyan]\n")
        console.print("1. Open https://opensea.io in your browser")
        console.print("2. Login with your wallet")
        console.print("3. Press F12 → Application → Cookies → https://opensea.io")
        console.print("4. Copy these values to .env:\n")
        console.print("   OPENSEA_AUTH_TOKEN=your_token_here")
        console.print("   OPENSEA_CSRF_TOKEN=your_csrf_here\n")
        
        # Open .env for editing
        edit = Prompt.ask("Open .env now?", choices=["y", "n"], default="y")
        if edit == "y":
            subprocess.run(["code", ".env"])


def multi_marketplace_menu():
    """Multi-marketplace menu"""
    console.print("\n[bold yellow]📊 MULTI-MARKETPLACE[/bold yellow]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Marketplace")
    table.add_column("Chains")
    table.add_column("Status")
    
    table.add_row("OpenSea", "ETH, Polygon, Base, ARB", "✅ Ready")
    table.add_row("Magic Eden", "Solana, ETH, Polygon", "✅ Ready")
    table.add_row("Tensor", "Solana", "✅ Ready")
    table.add_row("Blur", "Ethereum", "✅ Ready")
    
    console.print(table)
    console.print("\n[yellow]Use 'start.py --marketplace <name>' for specific marketplace[/yellow]")


def settings_menu():
    """Settings menu"""
    console.print("\n[bold yellow]⚙️  SETTINGS[/bold yellow]\n")
    
    console.print("Current configuration:\n")
    
    # Show current .env status
    env_vars = [
        "BASE_RPC_URL",
        "OPENSEA_AUTH_TOKEN",
        "FCFS_AGGRESSIVE_GAS",
    ]
    
    for var in env_vars:
        value = os.getenv(var, "")
        status = "✅ Set" if value else "❌ Not set"
        console.print(f"  {var}: {status}")
    
    console.print("\n[cyan]Edit .env to change settings:[/cyan]")
    console.print("  code .env\n")


def public_mint_menu():
    """Public mint auto menu - Simple interactive mode"""
    console.print("\n[bold yellow]🔥 PUBLIC MINT AUTO[/bold yellow]\n")
    console.print("[dim]No allowlist needed - just speed and timing![/dim]\n")
    
    # Step 1: Select chain
    chain = Prompt.ask(
        "Select chain",
        choices=["eth", "base", "arb", "polygon", "optimism"],
        default="base"
    )
    
    # Step 2: Contract address
    contract = Prompt.ask("NFT Contract Address")
    
    if not contract.startswith("0x"):
        console.print("[red]❌ Invalid contract address[/red]")
        return
    
    # Step 3: Mint details
    price = float(Prompt.ask("Mint price (ETH)", default="0.0"))
    quantity = IntPrompt.ask("Quantity", default=1)
    
    # Step 4: Timing mode
    console.print("\n[cyan]Select timing mode:[/cyan]")
    console.print("1. 🎯 Prewarm & Snipe (Recommended)")
    console.print("   - Start 5 menit sebelum launch")
    console.print("   - Auto-detect dan snipe saat live")
    console.print("   - Mirip FCFS mode")
    console.print("")
    console.print("2. ⏰ Scheduled (Exact Time)")
    console.print("   - Mint tepat waktu yang ditentukan")
    console.print("   - Contoh: 19:00:00")
    console.print("")
    console.print("3. ⚡ Immediate (Right Now)")
    console.print("   - Mint langsung tanpa tunggu")
    
    timing_mode = Prompt.ask(
        "Pilih mode",
        choices=["1", "2", "3"],
        default="1"
    )
    
    # Step 5: Gas strategy
    gas_strategy = Prompt.ask(
        "\nGas strategy",
        choices=["economy", "balanced", "aggressive"],
        default="balanced"
    )
    
    # Step 6: Wallet selection (if not already selected)
    manager = WalletManager()
    if not manager.selected_wallets:
        console.print("\n[yellow]⚠️ No wallet selected yet[/yellow]")
        wallets = select_wallet_interactive()
        if not wallets:
            console.print("[red]❌ Cancelled - no wallet selected[/red]")
            return
    
    # Execute based on timing mode
    if timing_mode == "1":
        # Prewarm mode (like FCFS)
        console.print("\n[bold cyan]🎯 PREWARM & SNIPE MODE[/bold cyan]")
        console.print("Bot akan polling contract sampai mint live...\n")
        
        cmd = [
            "python3", "auto_public_mint.py",
            "--contract", contract,
            "--chain", chain,
            "--price", str(price),
            "--quantity", str(quantity),
            "--strategy", gas_strategy,
        ]
        
        # Add multi-wallet flag if multiple wallets selected
        if len(manager.get_selected_wallets()) > 1:
            cmd.append("--multi-wallet")
        
        console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]\n")
        subprocess.run(cmd)
        
    elif timing_mode == "2":
        # Scheduled mode
        target_time = Prompt.ask(
            "\nMint time (HH:MM:SS format, 24h)",
            default="19:00:00"
        )
        
        # Parse time and validate
        from datetime import datetime
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            full_time = f"{today}T{target_time}"
            
            console.print(f"\n[bold cyan]⏰ SCHEDULED MODE[/bold cyan]")
            console.print(f"Target time: {target_time}")
            console.print("Bot akan pre-sign dan broadcast tepat waktu...\n")
            
            cmd = [
                "python3", "auto_public_mint.py",
                "--contract", contract,
                "--chain", chain,
                "--price", str(price),
                "--quantity", str(quantity),
                "--time", full_time,
                "--strategy", gas_strategy,
            ]
            
            if len(manager.get_selected_wallets()) > 1:
                cmd.append("--multi-wallet")
            
            console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]\n")
            subprocess.run(cmd)
            
        except Exception as e:
            console.print(f"[red]❌ Invalid time format: {e}[/red]")
            return
    
    else:
        # Immediate mode
        console.print("\n[bold cyan]⚡ IMMEDIATE MODE[/bold cyan]")
        console.print("Minting sekarang...\n")
        
        cmd = [
            "python3", "auto_public_mint.py",
            "--contract", contract,
            "--chain", chain,
            "--price", str(price),
            "--quantity", str(quantity),
            "--strategy", gas_strategy,
        ]
        
        if len(manager.get_selected_wallets()) > 1:
            cmd.append("--multi-wallet")
        
        console.print(f"[dim]Executing: {' '.join(cmd)}[/dim]\n")
        subprocess.run(cmd)


def scan_public_mints_menu():
    """Scan public mints menu"""
    console.print("\n[bold yellow]📡 SCAN PUBLIC MINTS[/bold yellow]\n")
    console.print("[dim]Monitor launchpads for upcoming public mints[/dim]\n")
    
    mode = Prompt.ask(
        "Mode",
        choices=["quick-scan", "monitor"],
        default="quick-scan"
    )
    
    if mode == "quick-scan":
        cmd = ["python3", "public_mint_monitor.py", "--scan"]
    else:
        chain = Prompt.ask(
            "Chain to monitor",
            choices=["base", "eth", "polygon", "arb", "all"],
            default="base"
        )
        auto_mint = Prompt.ask("Auto-mint when live?", choices=["y", "n"], default="n")
        max_price = float(Prompt.ask("Max auto-mint price (ETH)", default="0.05"))
        
        cmd = [
            "python3", "public_mint_monitor.py",
            "--monitor",
            "--chain", chain,
            "--max-price", str(max_price),
        ]
        if auto_mint == "y":
            cmd.append("--auto-mint")
    
    console.print(f"\n[bold cyan]Executing:[/bold cyan] {' '.join(cmd)}\n")
    
    # Run
    subprocess.run(cmd)


def wallet_selector_menu():
    """Wallet selector menu"""
    console.print("\n[bold yellow]💼 WALLET SELECTOR[/bold yellow]\n")
    
    # Show current wallets
    manager = WalletManager()
    
    if len(manager.wallets) == 0:
        console.print("[red]❌ No wallets configured![/red]")
        console.print("[yellow]Please configure wallets in .env file[/yellow]")
        return
    
    # Select wallet mode
    console.print("[cyan]Select mode:[/cyan]")
    console.print("1. Single Wallet (use one wallet)")
    console.print("2. Multi-Wallet (use multiple wallets)")
    console.print("3. All Wallets (use all configured wallets)")
    
    choice = console.input("\nSelect mode [1/2/3]: ").strip()
    
    if choice == "1":
        wallets = manager.select_wallet("single")
    elif choice == "2":
        wallets = manager.select_wallet("multi")
    elif choice == "3":
        wallets = manager.select_wallet("all")
    else:
        console.print("[red]Invalid choice[/red]")
        return
    
    if wallets:
        console.print(f"\n[green]✓ Selected {len(wallets)} wallet(s):[/green]")
        for w in wallets:
            console.print(f"  • {w.name}: {w.evm_address[:20]}...")
        
        # Save selection for current session
        manager.selected_wallets = [w.id for w in wallets]


def smart_gas_menu():
    """Smart gas optimizer menu"""
    console.print("\n[bold yellow]⛽ SMART GAS OPTIMIZER[/bold yellow]\n")
    
    # Show gas comparison
    SmartGasOptimizer.compare_chains()
    
    # Select chain for detailed view
    chain = Prompt.ask(
        "\nSelect chain for gas optimization",
        choices=["base", "arbitrum", "polygon", "optimism", "eth", "bsc"],
        default="base"
    )
    
    # Select strategy
    strategy = Prompt.ask(
        "Gas strategy",
        choices=["economy", "balanced", "aggressive"],
        default="balanced"
    )
    
    # Show recommendation
    opt = SmartGasOptimizer(chain)
    opt.set_strategy(strategy)
    
    console.print(Panel.fit(
        f"[bold cyan]{chain.upper()} Gas Configuration[/bold cyan]\n"
        f"Strategy: {strategy.upper()}",
        border_style="cyan"
    ))
    
    console.print(opt.get_recommendation())
    
    # Show estimated cost
    cost = opt.estimate_cost()
    console.print(f"\n[bold]Transaction Settings:[/bold]")
    console.print(f"  maxFeePerGas: {cost['max_fee_gwei']:.3f} gwei")
    console.print(f"  maxPriorityFeePerGas: {cost['priority_fee_gwei']:.3f} gwei")
    console.print(f"  gasLimit: {opt.config.gas_limit}")
    console.print(f"  Est. Cost: ~${cost['total_eth']:.6f} ETH")


def show_help():
    """Show help information"""
    help_text = """
[bold cyan]NFT MINTER BOT v3.1 - HELP[/bold cyan]

[bold yellow]Quick Commands:[/bold yellow]
  start_bot        - Launch this menu
  mint             - General minting
  mint_fcfs        - OpenSea FCFS specialist (allowlist)
  mint_public      - Auto public mint (no allowlist)
  mint_scan        - Scan public mints
  mint_info        - Check balances
  mint_auth        - Auto-fetch auth
  mint_wallet      - Select wallet
  mint_gas         - Check gas optimization

[bold yellow]Modes:[/bold yellow]
  1. OpenSea FCFS  - For allowlist/competitive mints
  2. Public Mint   - No allowlist needed, just speed
  3. Scan Monitor  - Auto-detect upcoming public mints
  4. Direct Mint   - Mint any contract directly
  5. Wallet Select - Choose single/multi wallet
  6. Smart Gas     - Optimize gas for L2 chains

[bold yellow]Supported Chains:[/bold yellow]
  EVM: ETH, Base, Arbitrum, Polygon, Optimism, Avalanche, BSC, Linea, Scroll
  Solana: Mainnet with Candy Machine v3

[bold yellow]Wallet Addresses:[/bold yellow]
  EVM: 0x5012E7Ea5F55C497B9e0Ed820229048aeF0f661f
  SOL: FkvuzuKruXDA1DAnofWPGBsfvSn5zRJZPxAJve5UYyB4

[bold yellow]Need Help?[/bold yellow]
  Repository: https://github.com/haybarch/nft-minter
    """
    console.print(help_text)


def main():
    """Main entry point"""
    print_banner()
    
    # Show wallet info on startup
    print_wallet_info()
    
    while True:
        try:
            choice = main_menu()
            
            if choice == 0:
                console.print("\n[green]👋 Goodbye! Happy minting! 🚀[/green]\n")
                break
            elif choice == 1:
                opensea_fcfs_menu()
            elif choice == 2:
                public_mint_menu()
            elif choice == 3:
                scan_public_mints_menu()
            elif choice == 4:
                direct_mint_menu()
            elif choice == 5:
                wallet_selector_menu()
            elif choice == 6:
                smart_gas_menu()
            elif choice == 7:
                check_balances()
            elif choice == 8:
                setup_opensea_auth()
            elif choice == 9:
                settings_menu()
            elif choice == 10:
                show_help()
            
            # Pause before showing menu again
            if choice != 0:
                console.print("\n[dim]Press Enter to continue...[/dim]")
                input()
                console.clear()
                print_banner()
                print_wallet_info()
                
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Use option 0 to exit properly.[/yellow]\n")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


if __name__ == "__main__":
    main()

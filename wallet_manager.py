#!/usr/bin/env python3
"""
Wallet Manager - Multi-Wallet System for NFT Minter
Supports wallet selection, multi-wallet minting, and wallet profiles
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from dotenv import load_dotenv

load_dotenv()
console = Console()


class WalletType(Enum):
    """Wallet types"""
    VPS_AIRDROP = "vps_airdrop"
    PERSONAL = "personal"
    BACKUP = "backup"
    MULTI = "multi"


@dataclass
class Wallet:
    """Wallet configuration"""
    id: str
    name: str
    type: WalletType
    evm_address: str
    evm_private_key: str
    sol_address: Optional[str] = None
    sol_private_key: Optional[str] = None
    is_active: bool = True
    description: str = ""


class WalletManager:
    """Manage multiple wallets with selector"""
    
    def __init__(self):
        self.wallets: List[Wallet] = []
        self.selected_wallets: List[str] = []  # IDs of selected wallets
        self._load_wallets_from_env()
    
    def _load_wallets_from_env(self):
        """Load wallet configurations from environment"""
        # Wallet 1: VPS Airdrop (default for minting)
        wallet_1_evm_addr = os.getenv("WALLET_1_EVM_ADDRESS", "0x5012E7Ea5F55C497B9e0Ed820229048aeF0f661f")
        wallet_1_evm_key = os.getenv("WALLET_1_EVM_PRIVATE_KEY", "0x7cc98417bf2da1fecb48562cc958a1763f7ea867e817e9e51be905ca98c23640")
        wallet_1_sol_addr = os.getenv("WALLET_1_SOL_ADDRESS", "FkvuzuKruXDA1DAnofWPGBsfvSn5zRJZPxAJve5UYyB4")
        wallet_1_sol_key = os.getenv("WALLET_1_SOL_PRIVATE_KEY", "16a52dfe6bbd282f63533176a7a26a6477ffd153aac32c2fd6004672a69bf6dadb448d60067f19bd313ce576b455fb6dfdc5bc24ebb6140e54cf9cabce07deef")
        
        if wallet_1_evm_key and wallet_1_evm_key != "0x":
            self.wallets.append(Wallet(
                id="wallet_1",
                name=os.getenv("WALLET_1_NAME", "VPS Airdrop"),
                type=WalletType.VPS_AIRDROP,
                evm_address=wallet_1_evm_addr,
                evm_private_key=wallet_1_evm_key,
                sol_address=wallet_1_sol_addr if wallet_1_sol_addr else None,
                sol_private_key=wallet_1_sol_key if wallet_1_sol_key else None,
                description="Default VPS wallet for airdrops"
            ))
        
        # Wallet 2: Personal (user's private wallet)
        wallet_2_evm_addr = os.getenv("WALLET_2_EVM_ADDRESS", "")
        wallet_2_evm_key = os.getenv("WALLET_2_EVM_PRIVATE_KEY", "")
        wallet_2_sol_addr = os.getenv("WALLET_2_SOL_ADDRESS", "")
        wallet_2_sol_key = os.getenv("WALLET_2_SOL_PRIVATE_KEY", "")
        
        if wallet_2_evm_key and wallet_2_evm_key.startswith("0x"):
            self.wallets.append(Wallet(
                id="wallet_2",
                name=os.getenv("WALLET_2_NAME", "Personal"),
                type=WalletType.PERSONAL,
                evm_address=wallet_2_evm_addr,
                evm_private_key=wallet_2_evm_key,
                sol_address=wallet_2_sol_addr if wallet_2_sol_addr else None,
                sol_private_key=wallet_2_sol_key if wallet_2_sol_key else None,
                description="Your personal wallet"
            ))
        
        # Wallet 3: Backup (optional)
        wallet_3_evm_addr = os.getenv("WALLET_3_EVM_ADDRESS", "")
        wallet_3_evm_key = os.getenv("WALLET_3_EVM_PRIVATE_KEY", "")
        
        if wallet_3_evm_key and wallet_3_evm_key.startswith("0x"):
            self.wallets.append(Wallet(
                id="wallet_3",
                name=os.getenv("WALLET_3_NAME", "Backup"),
                type=WalletType.BACKUP,
                evm_address=wallet_3_evm_addr,
                evm_private_key=wallet_3_evm_key,
                description="Backup wallet"
            ))
        
        # Legacy fallback: If no wallets loaded, use old format
        if not self.wallets:
            self._load_legacy_wallets()
    
    def _load_legacy_wallets(self):
        """Fallback to legacy wallet format"""
        base_key = os.getenv("BASE_PRIVATE_KEY", "")
        if base_key:
            self.wallets.append(Wallet(
                id="legacy",
                name="Legacy Wallet",
                type=WalletType.VPS_AIRDROP,
                evm_address="0x5012E7Ea5F55C497B9e0Ed820229048aeF0f661f",
                evm_private_key=base_key,
                description="Loaded from legacy config"
            ))
    
    def display_wallets(self) -> None:
        """Display all wallets in table"""
        table = Table(
            title="💼 Available Wallets",
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED
        )
        
        table.add_column("#", style="cyan", justify="center")
        table.add_column("Name", style="bright_white")
        table.add_column("Type", style="yellow")
        table.add_column("EVM Address", style="dim")
        table.add_column("SOL Address", style="dim")
        table.add_column("Status", style="green")
        
        for i, wallet in enumerate(self.wallets, 1):
            evm_short = f"{wallet.evm_address[:10]}...{wallet.evm_address[-6:]}" if len(wallet.evm_address) > 20 else wallet.evm_address
            sol_short = f"{wallet.sol_address[:8]}...{wallet.sol_address[-4:]}" if wallet.sol_address and len(wallet.sol_address) > 15 else (wallet.sol_address or "-")
            
            status = "✅ Active" if wallet.is_active else "❌ Inactive"
            
            table.add_row(
                str(i),
                wallet.name,
                wallet.type.value,
                evm_short,
                sol_short,
                status
            )
        
        console.print(table)
    
    def select_wallet(self, selection_mode: str = "single") -> List[Wallet]:
        """
        Interactive wallet selection
        
        Args:
            selection_mode: "single", "multi", or "all"
        
        Returns:
            List of selected wallets
        """
        if not self.wallets:
            console.print("[red]❌ No wallets configured![/red]")
            return []
        
        self.display_wallets()
        
        if selection_mode == "single":
            console.print("\n[cyan]Select wallet to use:[/cyan]")
            for i, wallet in enumerate(self.wallets, 1):
                console.print(f"  {i}. {wallet.name} ({wallet.evm_address[:15]}...)")
            
            try:
                choice = int(console.input("\nEnter number: ")) - 1
                if 0 <= choice < len(self.wallets):
                    selected = [self.wallets[choice]]
                    self.selected_wallets = [w.id for w in selected]
                    console.print(f"[green]✓ Selected: {selected[0].name}[/green]")
                    return selected
                else:
                    console.print("[red]Invalid selection[/red]")
                    return []
            except ValueError:
                console.print("[red]Invalid input[/red]")
                return []
        
        elif selection_mode == "multi":
            console.print("\n[cyan]Select wallets (comma-separated, e.g., 1,2):[/cyan]")
            for i, wallet in enumerate(self.wallets, 1):
                console.print(f"  {i}. {wallet.name}")
            
            try:
                choices = console.input("\nEnter numbers: ").strip()
                indices = [int(x.strip()) - 1 for x in choices.split(",")]
                selected = [self.wallets[i] for i in indices if 0 <= i < len(self.wallets)]
                self.selected_wallets = [w.id for w in selected]
                console.print(f"[green]✓ Selected {len(selected)} wallets[/green]")
                return selected
            except (ValueError, IndexError):
                console.print("[red]Invalid input[/red]")
                return []
        
        elif selection_mode == "all":
            self.selected_wallets = [w.id for w in self.wallets]
            console.print(f"[green]✓ Using all {len(self.wallets)} wallets[/green]")
            return self.wallets
        
        return []
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID"""
        for wallet in self.wallets:
            if wallet.id == wallet_id:
                return wallet
        return None
    
    def get_selected_wallets(self) -> List[Wallet]:
        """Get currently selected wallets"""
        return [w for w in self.wallets if w.id in self.selected_wallets]
    
    def get_evm_configs(self, chain: str) -> List[Dict]:
        """
        Get EVM configurations for selected wallets
        
        Returns list of dicts with rpc_url, private_key, etc.
        """
        configs = []
        selected = self.get_selected_wallets()
        
        for wallet in selected:
            rpc_url = os.getenv(f"{chain.upper()}_RPC_URL", "")
            if rpc_url and wallet.evm_private_key:
                configs.append({
                    "wallet_id": wallet.id,
                    "wallet_name": wallet.name,
                    "address": wallet.evm_address,
                    "private_key": wallet.evm_private_key,
                    "rpc_url": rpc_url,
                    "chain": chain,
                })
        
        return configs
    
    def add_wallet(
        self,
        name: str,
        wallet_type: WalletType,
        evm_address: str,
        evm_private_key: str,
        sol_address: Optional[str] = None,
        sol_private_key: Optional[str] = None,
    ) -> Wallet:
        """Add new wallet"""
        wallet_id = f"wallet_{len(self.wallets) + 1}"
        
        wallet = Wallet(
            id=wallet_id,
            name=name,
            type=wallet_type,
            evm_address=evm_address,
            evm_private_key=evm_private_key,
            sol_address=sol_address,
            sol_private_key=sol_private_key,
        )
        
        self.wallets.append(wallet)
        return wallet
    
    def save_to_env(self) -> bool:
        """Save wallet configuration to .env file"""
        try:
            env_file = ".env"
            
            # Read existing
            existing = ""
            if os.path.exists(env_file):
                with open(env_file, "r") as f:
                    existing = f.read()
            
            # Add wallet configs
            wallet_configs = []
            for i, wallet in enumerate(self.wallets, 1):
                wallet_configs.extend([
                    f"",
                    f"# Wallet {i}: {wallet.name}",
                    f"WALLET_{i}_NAME={wallet.name}",
                    f"WALLET_{i}_EVM_ADDRESS={wallet.evm_address}",
                    f"WALLET_{i}_EVM_PRIVATE_KEY={wallet.evm_private_key}",
                ])
                if wallet.sol_address:
                    wallet_configs.extend([
                        f"WALLET_{i}_SOL_ADDRESS={wallet.sol_address}",
                        f"WALLET_{i}_SOL_PRIVATE_KEY={wallet.sol_private_key}",
                    ])
            
            # Append to env
            with open(env_file, "a") as f:
                f.write("\n".join(wallet_configs))
            
            return True
        except Exception as e:
            console.print(f"[red]Error saving wallets: {e}[/red]")
            return False


def select_wallet_interactive() -> List[Wallet]:
    """
    Quick function to select wallet interactively
    Returns selected wallet(s)
    """
    manager = WalletManager()
    
    if len(manager.wallets) == 1:
        console.print(f"[green]✓ Using wallet: {manager.wallets[0].name}[/green]")
        return [manager.wallets[0]]
    
    console.print("\n[bold cyan]💼 Wallet Selection Mode[/bold cyan]")
    console.print("1. Single Wallet (use one wallet)")
    console.print("2. Multi-Wallet (use multiple wallets)")
    console.print("3. All Wallets (use all configured wallets)")
    
    choice = console.input("\nSelect mode [1/2/3]: ").strip()
    
    if choice == "1":
        return manager.select_wallet("single")
    elif choice == "2":
        return manager.select_wallet("multi")
    elif choice == "3":
        return manager.select_wallet("all")
    else:
        console.print("[red]Invalid choice, using default wallet[/red]")
        return [manager.wallets[0]] if manager.wallets else []


def main():
    """CLI entry point for wallet management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Wallet Manager")
    parser.add_argument("--list", "-l", action="store_true", help="List all wallets")
    parser.add_argument("--select", "-s", action="store_true", help="Select wallet interactively")
    parser.add_argument("--add", "-a", action="store_true", help="Add new wallet")
    
    args = parser.parse_args()
    
    manager = WalletManager()
    
    if args.list:
        manager.display_wallets()
    elif args.select:
        wallets = select_wallet_interactive()
        if wallets:
            console.print(f"\n[green]Selected {len(wallets)} wallet(s):[/green]")
            for w in wallets:
                console.print(f"  • {w.name}: {w.evm_address}")
    elif args.add:
        console.print("[yellow]Add wallet feature coming soon...[/yellow]")
    else:
        manager.display_wallets()


if __name__ == "__main__":
    main()

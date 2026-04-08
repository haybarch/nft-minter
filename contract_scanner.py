#!/usr/bin/env python3
"""
Contract Scanner - Auto-detect NFT mint contracts
Monitors blockchain for new NFT contracts and mint functions
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from web3 import Web3

console = Console()


@dataclass
class MintContract:
    """Detected mint contract"""
    address: str
    chain: str
    name: str
    mint_function: str
    mint_price: float
    is_verified: bool
    created_at: datetime
    source: str
    tx_count_24h: int


class ContractScanner:
    """
    Scan blockchain for new NFT mint contracts
    Auto-detect dari berbagai sumber
    """
    
    # Mint function signatures yang umum
    MINT_SIGNATURES = [
        "0x1249c58b",  # mint()
        "0x1113e9f8",  # publicMint(uint256)
        "0x8d53e3b9",  # mintPublic(uint256)
        "0x6bf2d7a5",  # mintTo(address)
        "0x40d097c3",  # safeMint(address,uint256)
        "0x60fe47b1",  # safeMint(address)
        "0x4e6ce0e5",  # mintNFT()
        "0x70a08231",  # balanceOf (ERC721 indicator)
    ]
    
    def __init__(self, rpc_url: str, chain: str = "base"):
        self.rpc_url = rpc_url
        self.chain = chain
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Content-Type": "application/json"}
            )
    
    def scan_recent_contracts(self, blocks_back: int = 100) -> List[MintContract]:
        """
        Scan recent blocks for new contracts with mint functions
        
        Args:
            blocks_back: Number of blocks to scan back
        """
        contracts = []
        
        try:
            latest = self.w3.eth.get_block('latest')
            latest_number = latest.number
            
            console.print(f"[dim]Scanning blocks {latest_number - blocks_back} to {latest_number}...[/dim]")
            
            for block_num in range(latest_number - blocks_back, latest_number + 1):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        # Check if transaction creates a contract
                        if not tx.to and tx.input:
                            # Contract creation - analyze bytecode
                            receipt = self.w3.eth.get_transaction_receipt(tx.hash)
                            if receipt and receipt.contractAddress:
                                contract_addr = receipt.contractAddress
                                
                                # Check if contract has mint functions
                                is_nft = self._check_contract_for_mint(contract_addr)
                                
                                if is_nft:
                                    contracts.append(MintContract(
                                        address=contract_addr,
                                        chain=self.chain,
                                        name=f"Contract-{contract_addr[:8]}",
                                        mint_function="detected",
                                        mint_price=0.0,
                                        is_verified=False,
                                        created_at=datetime.now(),
                                        source=f"block_{block_num}",
                                        tx_count_24h=0,
                                    ))
                        
                        # Check if transaction calls mint function
                        if tx.input and len(tx.input) >= 10:
                            selector = tx.input[:10].lower()
                            if selector in [s.lower() for s in self.MINT_SIGNATURES]:
                                if tx.to and tx.to not in [c.address for c in contracts]:
                                    contracts.append(MintContract(
                                        address=tx.to,
                                        chain=self.chain,
                                        name=f"Mint-Contract-{tx.to[:8]}",
                                        mint_function=selector,
                                        mint_price=0.0,
                                        is_verified=False,
                                        created_at=datetime.now(),
                                        source=f"tx_{tx.hash.hex()[:10]}",
                                        tx_count_24h=1,
                                    ))
                
                except Exception as e:
                    continue
            
        except Exception as e:
            console.print(f"[red]Scan error: {e}[/red]")
        
        return contracts
    
    def _check_contract_for_mint(self, address: str) -> bool:
        """
        Check if contract has mint-related functions
        """
        try:
            # Get bytecode
            code = self.w3.eth.get_code(Web3.to_checksum_address(address))
            bytecode = code.hex()
            
            # Check for mint function signatures in bytecode
            for sig in self.MINT_SIGNATURES:
                # Remove 0x prefix for searching
                sig_clean = sig.replace("0x", "")
                if sig_clean in bytecode:
                    return True
            
            return False
        except:
            return False
    
    async def scan_dexscreener(self) -> List[MintContract]:
        """Scan DEXScreener for new token pairs (proxy untuk NFT contracts)"""
        contracts = []
        
        try:
            async with self.session.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{self.chain}",
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Parse untuk detect new contracts
                    # Note: DEXScreener lebih fokus ke tokens, tapi bisa detect activity
        except Exception as e:
            console.print(f"[dim]DEXScreener scan skipped: {e}[/dim]")
        
        return contracts
    
    async def scan_moralis(self, api_key: Optional[str] = None) -> List[MintContract]:
        """
        Scan using Moralis API untuk NFT contracts
        Requires MORALIS_API_KEY
        """
        contracts = []
        
        api_key = api_key or os.getenv("MORALIS_API_KEY")
        if not api_key:
            return contracts
        
        try:
            headers = {
                "accept": "application/json",
                "X-API-Key": api_key,
            }
            
            # Get NFT contracts
            async with self.session.get(
                f"https://deep-index.moralis.io/api/v2/{self.chain}/nft/contracts",
                headers=headers,
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get("result", []):
                        contracts.append(MintContract(
                            address=item.get("token_address", ""),
                            chain=self.chain,
                            name=item.get("name", "Unknown"),
                            mint_function="detected",
                            mint_price=0.0,
                            is_verified=True,
                            created_at=datetime.now(),
                            source="moralis",
                            tx_count_24h=0,
                        ))
        except Exception as e:
            console.print(f"[dim]Moralis scan: {e}[/dim]")
        
        return contracts
    
    def display_contracts(self, contracts: List[MintContract]):
        """Display found contracts"""
        if not contracts:
            console.print("[yellow]No mint contracts found[/yellow]")
            return
        
        table = Table(
            title=f"🔍 Detected Mint Contracts ({self.chain.upper()})",
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Address", style="cyan")
        table.add_column("Name")
        table.add_column("Mint Function", style="dim")
        table.add_column("Source")
        table.add_column("Time", style="green")
        
        for c in contracts[:20]:  # Show max 20
            time_ago = "just now" if (datetime.now() - c.created_at).seconds < 60 else f"{(datetime.now() - c.created_at).seconds // 60}m ago"
            
            table.add_row(
                c.address[:20] + "...",
                c.name[:20],
                c.mint_function[:15],
                c.source,
                time_ago
            )
        
        console.print(table)
        console.print(f"\n[dim]Found {len(contracts)} contracts[/dim]")


class MintMonitor:
    """Monitor blockchain untuk new mint opportunities"""
    
    def __init__(self, chain: str = "base"):
        self.chain = chain
        self.rpc_url = self._get_rpc_url()
        self.scanner = ContractScanner(self.rpc_url, chain)
        self.known_contracts = set()
        
    def _get_rpc_url(self) -> str:
        """Get RPC URL from environment"""
        import os
        return os.getenv(f"{self.chain.upper()}_RPC_URL", "https://mainnet.base.org")
    
    async def monitor(self, check_interval: int = 60):
        """
        Continuously monitor for new mint contracts
        """
        await self.scanner.init_session()
        
        console.print(Panel.fit(
            f"[bold cyan]🔍 Mint Contract Monitor[/bold cyan]\n"
            f"Chain: {self.chain.upper()}\n"
            f"Check interval: {check_interval}s",
            border_style="cyan"
        ))
        
        console.print("[yellow]Press Ctrl+C to stop monitoring[/yellow]\n")
        
        try:
            while True:
                # Scan for new contracts
                contracts = self.scanner.scan_recent_contracts(blocks_back=10)
                
                # Filter new ones
                new_contracts = [
                    c for c in contracts 
                    if c.address not in self.known_contracts
                ]
                
                if new_contracts:
                    console.print(f"\n[bold green]🚨 {len(new_contracts)} NEW CONTRACTS DETECTED![/bold green]")
                    self.scanner.display_contracts(new_contracts)
                    
                    # Add to known
                    for c in new_contracts:
                        self.known_contracts.add(c.address)
                else:
                    console.print("[dim]No new contracts in last 10 blocks...[/dim]")
                
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
        finally:
            await self.scanner.session.close()


def quick_scan(chain: str = "base"):
    """Quick scan for mint contracts"""
    import os
    
    rpc_url = os.getenv(f"{chain.upper()}_RPC_URL", "https://mainnet.base.org")
    scanner = ContractScanner(rpc_url, chain)
    
    console.print(f"[cyan]Scanning {chain.upper()} for mint contracts...[/cyan]")
    
    contracts = scanner.scan_recent_contracts(blocks_back=50)
    
    if contracts:
        scanner.display_contracts(contracts)
        
        console.print("\n[bold green]💡 Quick Mint Commands:[/bold green]")
        for c in contracts[:5]:
            console.print(f"  mint_public --contract {c.address} --chain {chain} --price 0.01")
    else:
        console.print("[yellow]No contracts found in recent blocks[/yellow]")


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Contract Scanner - Auto-detect mint contracts")
    parser.add_argument("--scan", "-s", action="store_true", help="Quick scan")
    parser.add_argument("--monitor", "-m", action="store_true", help="Continuous monitor")
    parser.add_argument("--chain", "-c", default="base", 
                       choices=["eth", "base", "arb", "polygon", "optimism"])
    parser.add_argument("--blocks", "-b", type=int, default=50, help="Blocks to scan back")
    
    args = parser.parse_args()
    
    if args.monitor:
        monitor = MintMonitor(args.chain)
        asyncio.run(monitor.monitor())
    elif args.scan:
        quick_scan(args.chain)
    else:
        parser.print_help()


if __name__ == "__main__":
    import os
    main()

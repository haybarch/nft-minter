#!/usr/bin/env python3
"""
Public Mint Monitor - Auto-detect and mint public NFT drops
Monitors popular launchpads and mint calendars for upcoming public sales
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


@dataclass
class PublicMintEvent:
    """Represents a public mint event"""
    name: str
    collection: str
    contract_address: str
    chain: str
    mint_date: datetime
    mint_price: float
    supply: int
    website: str
    twitter: Optional[str] = None
    discord: Optional[str] = None
    status: str = "upcoming"  # upcoming, live, ended
    mint_function: str = "mint"  # mint, publicMint, etc.
    max_per_wallet: int = 1
    source: str = "unknown"  # launchpad, calendar, twitter


class LaunchpadScanner:
    """Scan popular NFT launchpads for public mints"""
    
    # Launchpad APIs and endpoints
    LAUNCHPADS = {
        "nftcalendar": {
            "url": "https://nftcalendar.io/api/upcoming",
            "method": "GET",
        },
        "mintify": {
            "url": "https://api.mintify.io/v1/drops",
            "method": "GET",
        },
        "premint": {
            "url": "https://api.premint.xyz/v1/public-projects",
            "method": "GET",
        },
        "hello_moon": {
            "url": "https://api.hellomoon.io/v1/nft-mints",
            "method": "POST",
        },
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.events: List[PublicMintEvent] = []
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                }
            )
    
    async def scan_nftcalendar(self) -> List[PublicMintEvent]:
        """Scan NFTCalendar.io for upcoming mints"""
        events = []
        
        try:
            async with self.session.get(
                "https://nftcalendar.io/api/upcoming",
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get("events", []):
                        event = PublicMintEvent(
                            name=item.get("title", "Unknown"),
                            collection=item.get("collection_name", ""),
                            contract_address=item.get("contract", ""),
                            chain=item.get("blockchain", "eth").lower(),
                            mint_date=datetime.fromisoformat(
                                item.get("date", datetime.now().isoformat())
                            ),
                            mint_price=float(item.get("price", 0)),
                            supply=int(item.get("supply", 0) or 0),
                            website=item.get("website", ""),
                            twitter=item.get("twitter", ""),
                            source="nftcalendar",
                            status="upcoming" if datetime.fromisoformat(
                                item.get("date")
                            ) > datetime.now() else "live",
                        )
                        events.append(event)
                        
        except Exception as e:
            console.print(f"[red]NFTCalendar scan error: {e}[/red]")
            
        return events
    
    async def scan_mintify(self) -> List[PublicMintEvent]:
        """Scan Mintify for upcoming drops"""
        events = []
        
        try:
            # Mintify requires API key
            api_key = self._get_api_key("MINTIFY_API_KEY")
            
            if not api_key:
                return events
            
            async with self.session.get(
                "https://api.mintify.io/v1/drops",
                headers={"Authorization": f"Bearer {api_key}"},
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get("drops", []):
                        event = PublicMintEvent(
                            name=item.get("name", "Unknown"),
                            collection=item.get("collection", ""),
                            contract_address=item.get("contract_address", ""),
                            chain=item.get("chain", "eth").lower(),
                            mint_date=datetime.fromtimestamp(
                                item.get("mint_timestamp", 0)
                            ),
                            mint_price=float(item.get("price", 0)),
                            supply=int(item.get("total_supply", 0) or 0),
                            website=item.get("website", ""),
                            twitter=item.get("twitter_url", ""),
                            source="mintify",
                            status=item.get("status", "upcoming"),
                        )
                        events.append(event)
                        
        except Exception as e:
            console.print(f"[red]Mintify scan error: {e}[/red]")
            
        return events
    
    async def scan_opensea_drops(self) -> List[PublicMintEvent]:
        """Scan OpenSea for upcoming drops"""
        events = []
        
        try:
            # OpenSea GraphQL query for upcoming drops
            query = """
            query UpcomingDrops {
                collections(
                    filter: {dropDate: {gte: "%s"}}
                    sort: DROP_DATE_ASC
                    first: 50
                ) {
                    edges {
                        node {
                            name
                            slug
                            drop {
                                dropDate
                                dropType
                            }
                            primaryContract
                            chain
                        }
                    }
                }
            }
            """ % datetime.now().strftime("%Y-%m-%d")
            
            async with self.session.post(
                "https://api.opensea.io/graphql/",
                json={"query": query},
                ssl=False
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for edge in data.get("data", {}).get("collections", {}).get("edges", []):
                        node = edge.get("node", {})
                        drop = node.get("drop", {})
                        
                        if drop:
                            event = PublicMintEvent(
                                name=node.get("name", "Unknown"),
                                collection=node.get("slug", ""),
                                contract_address=node.get("primaryContract", ""),
                                chain=node.get("chain", "eth").lower(),
                                mint_date=datetime.fromisoformat(
                                    drop.get("dropDate", "").replace("Z", "+00:00")
                                ),
                                mint_price=0,  # Need separate fetch
                                supply=0,  # Need separate fetch
                                website=f"https://opensea.io/collection/{node.get('slug', '')}",
                                source="opensea",
                                status="upcoming",
                            )
                            events.append(event)
                            
        except Exception as e:
            console.print(f"[red]OpenSea scan error: {e}[/red]")
            
        return events
    
    async def scan_all(self) -> List[PublicMintEvent]:
        """Scan all launchpads"""
        await self.init_session()
        
        all_events = []
        
        # Scan all sources concurrently
        tasks = [
            self.scan_nftcalendar(),
            self.scan_mintify(),
            self.scan_opensea_drops(),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_events.extend(result)
        
        # Sort by date
        all_events.sort(key=lambda x: x.mint_date)
        
        self.events = all_events
        return all_events
    
    def _get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key from environment"""
        import os
        return os.getenv(key_name)
    
    def filter_by_chain(self, chain: str) -> List[PublicMintEvent]:
        """Filter events by blockchain"""
        return [e for e in self.events if e.chain.lower() == chain.lower()]
    
    def filter_live(self) -> List[PublicMintEvent]:
        """Filter live mints"""
        now = datetime.now()
        return [
            e for e in self.events 
            if e.status == "live" or 
            (e.mint_date <= now and e.mint_date + timedelta(hours=24) > now)
        ]
    
    def filter_upcoming(self, hours: int = 24) -> List[PublicMintEvent]:
        """Filter upcoming mints within N hours"""
        now = datetime.now()
        future = now + timedelta(hours=hours)
        
        return [
            e for e in self.events
            if now < e.mint_date <= future
        ]
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()


class PublicMintAutomator:
    """Automate public minting with monitoring and execution"""
    
    def __init__(self):
        self.scanner = LaunchpadScanner()
        self.callbacks: List[Callable] = []
        self.monitoring = False
        
    def on_mint_detected(self, callback: Callable):
        """Register callback for mint detection"""
        self.callbacks.append(callback)
    
    async def monitor_and_mint(
        self,
        chain: Optional[str] = None,
        auto_mint: bool = False,
        max_price: float = 0.1,  # ETH
        check_interval: int = 60,  # seconds
    ):
        """
        Monitor for public mints and optionally auto-mint
        
        Args:
            chain: Filter by chain (eth, base, polygon, etc.)
            auto_mint: Automatically mint when detected
            max_price: Maximum price to auto-mint (ETH)
            check_interval: How often to check (seconds)
        """
        self.monitoring = True
        
        console.print(Panel.fit(
            f"[bold cyan]Public Mint Monitor[/bold cyan]\n"
            f"Chain: {chain or 'All'}\n"
            f"Auto-mint: {'Enabled' if auto_mint else 'Disabled'}\n"
            f"Max price: {max_price} ETH\n"
            f"Check interval: {check_interval}s",
            border_style="cyan"
        ))
        
        while self.monitoring:
            try:
                # Scan for new mints
                events = await self.scanner.scan_all()
                
                if chain:
                    events = [e for e in events if e.chain == chain.lower()]
                
                # Filter live and upcoming
                live = self.scanner.filter_live()
                upcoming = self.scanner.filter_upcoming(hours=6)
                
                if live:
                    console.print(f"\n[bold green]🚨 {len(live)} LIVE MINTS DETECTED![/bold green]")
                    self._display_events(live)
                    
                    # Notify callbacks
                    for callback in self.callbacks:
                        for event in live:
                            if event.mint_price <= max_price:
                                await callback(event)
                
                if upcoming:
                    console.print(f"\n[yellow]📅 {len(upcoming)} upcoming mints in next 6h[/yellow]")
                    self._display_events(upcoming[:5])  # Show top 5
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                console.print(f"[red]Monitor error: {e}[/red]")
                await asyncio.sleep(check_interval)
    
    def _display_events(self, events: List[PublicMintEvent]):
        """Display events in table"""
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Time", style="cyan")
        table.add_column("Name", style="bright_white")
        table.add_column("Chain")
        table.add_column("Price")
        table.add_column("Supply")
        table.add_column("Contract", style="dim")
        
        for event in events:
            time_str = event.mint_date.strftime("%H:%M")
            table.add_row(
                time_str,
                event.name[:30],
                event.chain.upper(),
                f"{event.mint_price:.3f} Ξ",
                str(event.supply) if event.supply > 0 else "?",
                event.contract_address[:15] + "..." if event.contract_address else "-"
            )
        
        console.print(table)
    
    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
    
    async def close(self):
        """Cleanup"""
        await self.scanner.close()


async def quick_public_mint_scan():
    """Quick scan for public mints"""
    scanner = LaunchpadScanner()
    
    try:
        console.print("[cyan]Scanning for public mints...[/cyan]")
        events = await scanner.scan_all()
        
        if events:
            console.print(f"\n[green]Found {len(events)} upcoming mints[/green]")
            
            # Show live first
            live = scanner.filter_live()
            if live:
                console.print(f"\n[bold red]🔥 LIVE NOW: {len(live)} mints[/bold red]")
                for e in live:
                    console.print(f"  • {e.name} ({e.chain}) - {e.website}")
            
            # Show upcoming
            upcoming = scanner.filter_upcoming(hours=24)
            if upcoming:
                console.print(f"\n[yellow]📅 Next 24h: {len(upcoming)} mints[/yellow]")
                for e in upcoming[:10]:
                    time_left = e.mint_date - datetime.now()
                    hours = int(time_left.total_seconds() / 3600)
                    console.print(f"  • {e.name} in {hours}h - {e.website}")
        else:
            console.print("[yellow]No upcoming mints found[/yellow]")
            
    finally:
        await scanner.close()


async def monitor_public_mints(
    chain: str = "base",
    auto_mint: bool = False,
    max_price: float = 0.05,
):
    """Monitor public mints with optional auto-mint"""
    automator = PublicMintAutomator()
    
    # Setup auto-mint callback
    if auto_mint:
        async def on_detected(event: PublicMintEvent):
            console.print(f"\n[bold green]🎯 Auto-minting: {event.name}[/bold green]")
            # Import and call mint function
            from evm_minter import EVMMinter
            from config import EVMChainConfig
            import os
            
            config = EVMChainConfig(
                name=event.chain,
                rpc_url=os.getenv(f"{event.chain.upper()}_RPC_URL", ""),
                private_key=os.getenv(f"{event.chain.upper()}_PRIVATE_KEY", ""),
                chain_id=8453 if event.chain == "base" else 1,
            )
            
            minter = EVMMinter(config)
            minter.set_contract(event.contract_address)
            
            result = minter.mint(
                quantity=1,
                mint_price_eth=event.mint_price,
                max_retries=5,
            )
            
            if result.success:
                console.print(f"[green]✓ Minted! TX: {result.tx_hash[:20]}...[/green]")
            else:
                console.print(f"[red]✗ Failed: {result.error}[/red]")
        
        automator.on_mint_detected(on_detected)
    
    try:
        await automator.monitor_and_mint(
            chain=chain,
            auto_mint=auto_mint,
            max_price=max_price,
            check_interval=30,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")
        automator.stop()
    finally:
        await automator.close()


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Public Mint Monitor")
    parser.add_argument("--scan", "-s", action="store_true", help="Quick scan")
    parser.add_argument("--monitor", "-m", action="store_true", help="Start monitoring")
    parser.add_argument("--chain", "-c", default="base", help="Chain to monitor")
    parser.add_argument("--auto-mint", "-a", action="store_true", help="Auto-mint enabled")
    parser.add_argument("--max-price", "-p", type=float, default=0.05, help="Max price (ETH)")
    
    args = parser.parse_args()
    
    if args.scan:
        asyncio.run(quick_public_mint_scan())
    elif args.monitor:
        asyncio.run(monitor_public_mints(
            chain=args.chain,
            auto_mint=args.auto_mint,
            max_price=args.max_price,
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

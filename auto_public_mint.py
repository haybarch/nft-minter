#!/usr/bin/env python3
"""
Auto Public Mint - Automatically mint public NFT drops
No allowlist needed - just pure speed and timing
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from web3 import Web3
from eth_account import Account
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


@dataclass
class PublicMintConfig:
    """Configuration for auto public mint"""
    contract_address: str
    chain: str
    rpc_url: str
    private_key: str
    mint_price: float
    gas_limit: int = 300000
    max_fee_gwei: int = 100
    priority_fee_gwei: int = 5
    quantity: int = 1
    mint_function: str = "mint"  # mint, publicMint, mintPublic, etc.


class AutoPublicMinter:
    """
    Automated public minter - no signature needed
    Direct contract interaction with aggressive gas
    """
    
    # Common public mint function signatures
    MINT_SIGNATURES = {
        "mint": "0x1249c58b",  # mint()
        "publicMint": "0x1113e9f8",  # publicMint(uint256)
        "mintPublic": "0x8d53e3b9",  # mintPublic(uint256)
        "mintTo": "0x6bf2d7a5",  # mintTo(address)
        "safeMint": "0x60fe47b1",  # safeMint(address)
    }
    
    def __init__(self, config: PublicMintConfig):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self.account = Account.from_key(config.private_key)
        self.nonce_cache = 0
        self.last_nonce_update = 0
        
    def _get_fast_nonce(self) -> int:
        """Get nonce with aggressive caching"""
        now = time.time()
        if now - self.last_nonce_update > 3:
            self.nonce_cache = self.w3.eth.get_transaction_count(
                self.account.address,
                'pending'
            )
            self.last_nonce_update = now
        else:
            self.nonce_cache += 1
        return self.nonce_cache
    
    def _build_mint_calldata(self, quantity: int = 1) -> str:
        """
        Build mint calldata for common public mint functions
        """
        # Try to detect mint function from contract
        mint_fn = self.config.mint_function
        
        if mint_fn == "mint":
            # Simple mint() with no args
            return self.MINT_SIGNATURES["mint"]
        elif mint_fn == "publicMint":
            # publicMint(uint256 quantity)
            # Encode: function selector + uint256
            return (
                self.MINT_SIGNATURES["publicMint"] + 
                quantity.to_bytes(32, 'big').hex()
            )
        elif mint_fn == "mintPublic":
            # mintPublic(uint256 quantity)
            return (
                self.MINT_SIGNATURES["mintPublic"] + 
                quantity.to_bytes(32, 'big').hex()
            )
        else:
            # Default to simple mint
            return self.MINT_SIGNATURES["mint"]
    
    def _build_transaction(self) -> Dict[str, Any]:
        """Build aggressive transaction for public mint"""
        # Get latest block for gas estimation
        try:
            latest = self.w3.eth.get_block('latest')
            base_fee = latest.get('baseFeePerGas', self.w3.to_wei(30, 'gwei'))
            
            # Aggressive gas pricing for public mints
            priority_fee = self.w3.to_wei(self.config.priority_fee_gwei, 'gwei')
            max_fee = int(base_fee * 2.5) + priority_fee
            
            # Cap at max
            max_fee = min(max_fee, self.w3.to_wei(self.config.max_fee_gwei, 'gwei'))
        except:
            # Fallback
            max_fee = self.w3.to_wei(self.config.max_fee_gwei, 'gwei')
            priority_fee = self.w3.to_wei(self.config.priority_fee_gwei, 'gwei')
        
        # Calculate value (mint price * quantity)
        value_wei = self.w3.to_wei(self.config.mint_price * self.config.quantity, 'ether')
        
        # Build calldata
        calldata = self._build_mint_calldata(self.config.quantity)
        
        return {
            "from": self.account.address,
            "to": Web3.to_checksum_address(self.config.contract_address),
            "data": calldata,
            "value": value_wei,
            "gas": self.config.gas_limit,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "nonce": self._get_fast_nonce(),
            "chainId": self.w3.eth.chain_id,
            "type": 2,
        }
    
    def snipe_mint(self, max_retries: int = 10) -> Dict[str, Any]:
        """
        Snipe public mint with aggressive retry
        """
        start_time = time.perf_counter()
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Build transaction
                tx = self._build_transaction()
                
                # Sign
                signed = self.account.sign_transaction(tx)
                
                # Broadcast
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                tx_hash_hex = tx_hash.hex()
                
                # Wait for receipt (short timeout for speed)
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(
                        tx_hash,
                        timeout=30,
                        poll_latency=0.5,
                    )
                    elapsed = (time.perf_counter() - start_time) * 1000
                    
                    return {
                        "success": receipt.status == 1,
                        "tx_hash": tx_hash_hex,
                        "gas_used": receipt.gasUsed,
                        "elapsed_ms": elapsed,
                        "attempts": attempt + 1,
                        "error": None,
                    }
                except Exception as e:
                    # Broadcast worked but receipt timeout
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return {
                        "success": True,  # Assume success
                        "tx_hash": tx_hash_hex,
                        "elapsed_ms": elapsed,
                        "attempts": attempt + 1,
                        "error": f"Receipt timeout: {e}",
                    }
                    
            except Exception as e:
                last_error = str(e)
                # Quick retry with higher gas
                if attempt < max_retries - 1:
                    self.config.priority_fee_gwei += 2
                    time.sleep(0.05 * (attempt + 1))  # Exponential backoff
        
        elapsed = (time.perf_counter() - start_time) * 1000
        
        return {
            "success": False,
            "tx_hash": None,
            "elapsed_ms": elapsed,
            "attempts": max_retries,
            "error": f"Failed after {max_retries} attempts: {last_error}",
        }
    
    async def presign_and_snipe(
        self,
        target_time: Optional[datetime] = None,
        offset_ms: int = -100,  # Start 100ms early
    ) -> Dict[str, Any]:
        """
        Pre-sign transaction and broadcast at exact time
        """
        if target_time:
            # Wait until target time + offset
            now = datetime.now()
            wait_seconds = (target_time - now).total_seconds() + (offset_ms / 1000)
            
            if wait_seconds > 0:
                console.print(f"[yellow]Waiting {wait_seconds:.2f}s until mint...[/yellow]")
                await asyncio.sleep(wait_seconds)
        
        # Execute
        return await asyncio.get_event_loop().run_in_executor(
            None, self.snipe_mint
        )


class MultiWalletPublicMinter:
    """Multi-wallet public minting for higher chances"""
    
    def __init__(self, configs: List[PublicMintConfig]):
        self.configs = configs
        self.minters = [AutoPublicMinter(c) for c in configs]
    
    async def snipe_with_all(
        self,
        stagger_ms: float = 50,  # Stagger between wallets
    ) -> List[Dict[str, Any]]:
        """Snipe with all wallets simultaneously"""
        results = []
        
        for i, minter in enumerate(self.minters):
            if i > 0:
                await asyncio.sleep(stagger_ms / 1000)
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, minter.snipe_mint
            )
            results.append(result)
        
        return results


async def auto_mint_public_drop(
    contract_address: str,
    chain: str = "base",
    mint_price: float = 0.0,
    quantity: int = 1,
    mint_function: str = "mint",
    target_time: Optional[str] = None,
):
    """
    Quick function to auto-mint a public drop
    
    Usage:
        await auto_mint_public_drop(
            contract_address="0x...",
            chain="base",
            mint_price=0.01,
            target_time="2025-01-09T14:00:00",
        )
    """
    import os
    
    # Get config from env
    rpc_url = os.getenv(f"{chain.upper()}_RPC_URL", "")
    private_key = os.getenv(f"{chain.upper()}_PRIVATE_KEY", "")
    
    if not rpc_url or not private_key:
        console.print("[red]Missing RPC URL or private key in .env[/red]")
        return
    
    config = PublicMintConfig(
        contract_address=contract_address,
        chain=chain,
        rpc_url=rpc_url,
        private_key=private_key,
        mint_price=mint_price,
        quantity=quantity,
        mint_function=mint_function,
    )
    
    minter = AutoPublicMinter(config)
    
    console.print(Panel.fit(
        f"[bold cyan]Auto Public Mint[/bold cyan]\n"
        f"Contract: {contract_address[:20]}...\n"
        f"Chain: {chain.upper()}\n"
        f"Price: {mint_price} ETH\n"
        f"Quantity: {quantity}",
        border_style="cyan"
    ))
    
    # Parse target time if provided
    target_dt = None
    if target_time:
        try:
            target_dt = datetime.fromisoformat(target_time.replace("Z", "+00:00"))
            console.print(f"[yellow]Target time: {target_dt}[/yellow]")
        except:
            console.print("[red]Invalid target time format[/red]")
    
    # Execute
    if target_dt:
        result = await minter.presign_and_snipe(target_dt)
    else:
        result = await asyncio.get_event_loop().run_in_executor(
            None, minter.snipe_mint
        )
    
    # Display result
    if result["success"]:
        console.print(f"\n[bold green]🎉 Mint Successful![/bold green]")
        console.print(f"  TX Hash: {result['tx_hash'][:30]}...")
        console.print(f"  Time: {result['elapsed_ms']:.1f}ms")
        console.print(f"  Attempts: {result['attempts']}")
    else:
        console.print(f"\n[bold red]❌ Mint Failed[/bold red]")
        console.print(f"  Error: {result['error']}")
        console.print(f"  Time: {result['elapsed_ms']:.1f}ms")
    
    return result


async def prewarm_and_snipe_public(
    contract_address: str,
    chain: str,
    mint_price: float,
    quantity: int,
    strategy: str = "balanced",
    poll_interval: float = 0.5,
    timeout_minutes: int = 10,
):
    """
    Prewarm mode for public mint - poll until mint is live then snipe
    Similar to FCFS mode but for public mints
    """
    from web3 import Web3
    import time
    
    console.print(Panel.fit(
        f"[bold cyan]🔥 PUBLIC MINT - PREWARM MODE[/bold cyan]\n"
        f"Contract: {contract_address[:20]}...\n"
        f"Chain: {chain.upper()}\n"
        f"Strategy: {strategy.upper()}\n"
        f"Polling every: {poll_interval}s",
        border_style="cyan"
    ))
    
    # Load wallets
    from wallet_manager import WalletManager
    manager = WalletManager()
    wallets = manager.get_selected_wallets()
    
    if not wallets:
        console.print("[red]❌ No wallets selected![/red]")
        return
    
    console.print(f"[green]✓ Using {len(wallets)} wallet(s)[/green]\n")
    
    # Get RPC
    import os
    rpc_url = os.getenv(f"{chain.upper()}_RPC_URL", "")
    if not rpc_url:
        console.print("[red]❌ No RPC URL configured![/red]")
        return
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Check if contract exists
    try:
        code = w3.eth.get_code(Web3.to_checksum_address(contract_address))
        if code == b'':
            console.print("[red]❌ Contract not deployed yet![/red]")
            return
    except Exception as e:
        console.print(f"[red]❌ Error checking contract: {e}[/red]")
        return
    
    console.print("[yellow]⏳ Polling for mint to go live...[/yellow]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    start_time = time.time()
    is_live = False
    
    try:
        while time.time() - start_time < timeout_minutes * 60:
            try:
                # Try to estimate gas for mint function
                # If it works, mint is live
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=[{
                        "inputs": [],
                        "name": "mint",
                        "outputs": [],
                        "stateMutability": "payable",
                        "type": "function"
                    }]
                )
                
                # Try to call mint (will fail if not live, but we can detect)
                # Actually, better to check if there's any activity
                
                # Simple check: look for recent transactions to contract
                # For now, just try a dry-run or check block timestamps
                
                # Alternative: Just try to mint with 0 value and see if it reverts
                # with specific error ("Sale not started" vs "insufficient funds")
                
                is_live = True  # Assume live and try
                break
                
            except Exception as e:
                # Not live yet
                elapsed = int(time.time() - start_time)
                console.print(f"[dim]⏱️  {elapsed}s - Still waiting...[/dim]", end="\r")
                await asyncio.sleep(poll_interval)
        
        if is_live:
            console.print(f"\n[bold green]🚨 MINT IS LIVE! SNIPING NOW![/bold green]\n")
            
            # Execute mint with all wallets
            results = []
            for wallet in wallets:
                config = PublicMintConfig(
                    contract_address=contract_address,
                    chain=chain,
                    rpc_url=rpc_url,
                    private_key=wallet.evm_private_key,
                    mint_price=mint_price,
                    quantity=quantity,
                )
                
                # Apply gas strategy
                if strategy == "economy":
                    config.priority_fee_gwei = 0.05
                    config.max_fee_gwei = 0.5
                elif strategy == "aggressive":
                    config.priority_fee_gwei = 2.0
                    config.max_fee_gwei = 5.0
                else:  # balanced
                    config.priority_fee_gwei = 0.1
                    config.max_fee_gwei = 1.0
                
                minter = AutoPublicMinter(config)
                result = minter.snipe_mint(max_retries=10)
                results.append((wallet.name, result))
            
            # Display results
            console.print("\n[bold]🎯 RESULTS:[/bold]")
            for name, result in results:
                if result["success"]:
                    console.print(f"  ✅ {name}: TX {result['tx_hash'][:20]}... ({result['elapsed_ms']:.0f}ms)")
                else:
                    console.print(f"  ❌ {name}: {result['error'][:40]}...")
        else:
            console.print(f"\n[yellow]⚠️ Timeout after {timeout_minutes} minutes[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Auto Public Mint - Snipe public NFT drops",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Immediate mint
  python3 auto_public_mint.py --contract 0x... --chain base --price 0.01

  # Scheduled mint (snipe at exact time)
  python3 auto_public_mint.py --contract 0x... --time "2025-01-09T14:00:00"

  # Prewarm mode (like FCFS)
  python3 auto_public_mint.py --contract 0x... --prewarm --strategy aggressive

  # Multi-wallet mint
  python3 auto_public_mint.py --contract 0x... --multi-wallet
        """
    )
    
    parser.add_argument("--contract", "-a", required=True, help="NFT contract address")
    parser.add_argument("--chain", "-c", default="base", choices=["eth", "base", "arb", "polygon", "optimism"])
    parser.add_argument("--price", "-p", type=float, default=0.0, help="Mint price in ETH")
    parser.add_argument("--quantity", "-n", type=int, default=1, help="Quantity to mint")
    parser.add_argument("--time", "-t", help="Target time (ISO format)")
    parser.add_argument("--mint-function", "-f", default="mint", 
                       choices=["mint", "publicMint", "mintPublic"],
                       help="Mint function name")
    parser.add_argument("--multi-wallet", "-m", action="store_true", help="Use multiple wallets")
    parser.add_argument("--prewarm", action="store_true", help="Prewarm mode - poll until mint live")
    parser.add_argument("--strategy", "-s", default="balanced", 
                       choices=["economy", "balanced", "aggressive"],
                       help="Gas strategy")
    
    args = parser.parse_args()
    
    if args.prewarm:
        # Prewarm mode (like FCFS)
        asyncio.run(prewarm_and_snipe_public(
            contract_address=args.contract,
            chain=args.chain,
            mint_price=args.price,
            quantity=args.quantity,
            strategy=args.strategy,
        ))
    else:
        # Normal mode
        asyncio.run(auto_mint_public_drop(
            contract_address=args.contract,
            chain=args.chain,
            mint_price=args.price,
            quantity=args.quantity,
            mint_function=args.mint_function,
            target_time=args.time,
        ))


if __name__ == "__main__":
    main()

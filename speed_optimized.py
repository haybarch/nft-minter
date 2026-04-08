#!/usr/bin/env python3
"""
Speed Optimized Minter - Ultra-Fast Async Batch Operations
Pre-signed transactions, connection pooling, and parallel execution
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from web3 import Web3
from eth_account import Account

from opensea_minter import OpenSeaFCFSMinter, OpenSeaConfig, OpenSeaMintResult
from evm_minter import EVMMinter, EVMChainConfig
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


@dataclass
class SpeedConfig:
    """Configuration for speed optimizations"""
    # Connection pooling
    max_connections: int = 100
    max_connections_per_host: int = 50
    
    # Parallel execution
    max_workers: int = 10
    batch_size: int = 5
    
    # Timing
    request_timeout: float = 3.0
    retry_delay: float = 0.05  # 50ms
    poll_interval: float = 0.1
    
    # Pre-signing
    pre_sign_transactions: bool = True
    presign_cache_duration: int = 30  # seconds
    
    # Aggressive modes
    aggressive_gas: bool = True
    skip_preflight: bool = True
    

class PreSignedTransactionPool:
    """
    Pre-sign transactions before mint goes live
    Then broadcast instantly when ready
    """
    
    def __init__(self, config: SpeedConfig):
        self.config = config
        self._presigned_txs: Dict[str, Any] = {}
        self._account_cache: Dict[str, Account] = {}
    
    def pre_sign_mint_tx(
        self,
        wallet_key: str,
        contract_address: str,
        calldata: str,
        value: int,
        chain_config: EVMChainConfig,
    ) -> str:
        """
        Pre-sign a mint transaction
        Returns the signed transaction hex ready to broadcast
        """
        # Get or create account
        if wallet_key not in self._account_cache:
            self._account_cache[wallet_key] = Account.from_key(wallet_key)
        
        account = self._account_cache[wallet_key]
        
        # Build transaction
        w3 = Web3(Web3.HTTPProvider(chain_config.rpc_url))
        
        try:
            latest = w3.eth.get_block('latest')
            base_fee = latest.get('baseFeePerGas', w3.to_wei(30, 'gwei'))
            
            if self.config.aggressive_gas:
                priority_fee = w3.to_wei(5, 'gwei')  # Higher for speed
                max_fee = int(base_fee * 2.5) + priority_fee
            else:
                priority_fee = w3.to_wei(2, 'gwei')
                max_fee = int(base_fee * 2) + priority_fee
        except:
            max_fee = w3.to_wei(100, 'gwei')
            priority_fee = w3.to_wei(5, 'gwei')
        
        tx = {
            "from": account.address,
            "to": Web3.to_checksum_address(contract_address),
            "data": calldata,
            "value": value,
            "gas": chain_config.gas_limit,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "chainId": chain_config.chain_id,
            "type": 2,
        }
        
        # Sign without nonce - will be added at broadcast time
        signed = account.sign_transaction(tx)
        
        tx_key = f"{wallet_key[:10]}_{contract_address[:10]}"
        self._presigned_txs[tx_key] = {
            "signed": signed,
            "timestamp": time.time(),
            "tx_dict": tx,
        }
        
        return signed.rawTransaction.hex()
    
    def broadcast_presigned(
        self,
        wallet_key: str,
        contract_address: str,
        rpc_url: str,
        nonce: int,
    ) -> Optional[str]:
        """Broadcast a pre-signed transaction with nonce"""
        tx_key = f"{wallet_key[:10]}_{contract_address[:10]}"
        cached = self._presigned_txs.get(tx_key)
        
        if not cached:
            return None
        
        # Check expiry
        if time.time() - cached["timestamp"] > self.config.presign_cache_duration:
            return None
        
        # Re-sign with correct nonce
        account = self._account_cache.get(wallet_key)
        if not account:
            return None
        
        tx_dict = cached["tx_dict"].copy()
        tx_dict["nonce"] = nonce
        
        signed = account.sign_transaction(tx_dict)
        
        # Broadcast
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        try:
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            return tx_hash.hex()
        except Exception as e:
            console.print(f"[red]Broadcast failed: {e}[/red]")
            return None


class AsyncBatchMinter:
    """
    High-performance async batch minter
    For minting multiple NFTs or using multiple wallets simultaneously
    """
    
    def __init__(self, config: SpeedConfig = None):
        self.config = config or SpeedConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    async def init_session(self):
        """Initialize aiohttp session with optimized settings"""
        if not self.session:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections_per_host,
                enable_cleanup_closed=True,
                force_close=False,
                ttl_dns_cache=300,
                use_dns_cache=True,
                family=0,  # Allow IPv4 and IPv6
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.config.request_timeout,
                connect=1.0,
                sock_read=2.0,
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
    
    async def batch_mint_opensea(
        self,
        configs: List[OpenSeaConfig],
        contract_address: str,
        token_id: str = "0",
        quantity: str = "1",
    ) -> List[OpenSeaMintResult]:
        """
        Batch mint on OpenSea with multiple wallets simultaneously
        Maximum speed for FCFS drops
        """
        await self.init_session()
        
        # Create minters
        minters = [OpenSeaFCFSMinter(cfg) for cfg in configs]
        
        # Initialize all sessions in parallel
        init_tasks = [m.graphql.init_session() for m in minters]
        await asyncio.gather(*init_tasks)
        
        # Create mint tasks
        mint_tasks = [
            m.snipe_mint(contract_address, token_id, quantity, max_retries=5)
            for m in minters
        ]
        
        # Execute all mints concurrently
        results = await asyncio.gather(*mint_tasks, return_exceptions=True)
        
        # Cleanup
        close_tasks = [m.close() for m in minters]
        await asyncio.gather(*close_tasks)
        
        # Process results
        output = []
        for result in results:
            if isinstance(result, Exception):
                output.append(OpenSeaMintResult(
                    success=False,
                    error=str(result)
                ))
            else:
                output.append(result)
        
        return output
    
    async def staggered_mint(
        self,
        mint_fn: Callable,
        wallets: List[Any],
        delay_ms: float = 50.0,
    ) -> List[Any]:
        """
        Staggered mint - slight delay between each wallet
        Helps avoid rate limits while still being fast
        """
        results = []
        
        for i, wallet in enumerate(wallets):
            if i > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            
            try:
                result = await mint_fn(wallet)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})
        
        return results
    
    async def race_mint(
        self,
        mint_fns: List[Callable],
        stop_on_first_success: bool = True,
    ) -> Dict[str, Any]:
        """
        Race condition mint - try multiple methods simultaneously
        Return the first successful one
        """
        tasks = [asyncio.create_task(fn()) for fn in mint_fns]
        
        if stop_on_first_success:
            # Wait for first success
            pending = set(tasks)
            results = {}
            
            while pending:
                done, pending = await asyncio.wait(
                    pending,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    try:
                        result = task.result()
                        if getattr(result, 'success', False):
                            # Cancel remaining tasks
                            for t in pending:
                                t.cancel()
                            return {"winner": result, "method": mint_fns[tasks.index(task)]}
                    except Exception as e:
                        results[f"error_{tasks.index(task)}"] = str(e)
            
            return results
        else:
            # Wait for all
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return {f"method_{i}": r for i, r in enumerate(results)}
    
    async def poll_drop_status(
        self,
        check_fn: Callable,
        interval: float = 0.5,
        timeout: float = 300.0,
    ) -> Optional[Any]:
        """
        Poll drop status until live or timeout
        """
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                status = await check_fn()
                if status:
                    return status
            except Exception:
                pass
            
            await asyncio.sleep(interval)
        
        return None
    
    async def close(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
            self.session = None
        self._executor.shutdown(wait=False)


class LatencyOptimizer:
    """
    Optimize for lowest possible latency
    """
    
    @staticmethod
    def measure_rpc_latency(rpc_url: str, samples: int = 5) -> float:
        """Measure average RPC latency"""
        latencies = []
        
        for _ in range(samples):
            start = time.perf_counter()
            try:
                import requests
                resp = requests.post(
                    rpc_url,
                    json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                    timeout=5
                )
                if resp.status_code == 200:
                    latencies.append(time.perf_counter() - start)
            except:
                pass
        
        return sum(latencies) / len(latencies) if latencies else float('inf')
    
    @staticmethod
    def select_fastest_rpc(rpc_urls: List[str]) -> str:
        """Select fastest RPC from list"""
        results = []
        
        for url in rpc_urls:
            latency = LatencyOptimizer.measure_rpc_latency(url)
            results.append((url, latency))
        
        results.sort(key=lambda x: x[1])
        return results[0][0] if results else rpc_urls[0]


# Quick performance functions
async def mint_single_fast(
    chain: str,
    contract: str,
    private_key: str,
    rpc_url: str,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Single-shot mint optimized for maximum speed
    """
    from config import EVMChainConfig
    
    start = time.perf_counter()
    
    config = EVMChainConfig(
        name=chain,
        rpc_url=rpc_url,
        private_key=private_key,
        chain_id=1 if chain == "eth" else 8453,
    )
    
    minter = EVMMinter(config)
    result = minter.mint(quantity=1, max_retries=1)
    
    elapsed = time.perf_counter() - start
    
    return {
        "success": result.success,
        "tx_hash": result.tx_hash,
        "elapsed_ms": elapsed * 1000,
        "error": result.error,
    }


async def benchmark_mint_speed(
    configs: List[Any],
    contract: str,
    iterations: int = 3,
) -> Dict[str, Any]:
    """
    Benchmark minting speed
    """
    times = []
    
    for i in range(iterations):
        start = time.perf_counter()
        
        # Simulate mint (without actual broadcast in benchmark mode)
        await asyncio.sleep(0.001)  # Placeholder
        
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    
    return {
        "avg_ms": sum(times) / len(times) * 1000,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
        "samples": iterations,
    }

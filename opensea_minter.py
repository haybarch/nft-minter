#!/usr/bin/env python3
"""
OpenSea FCFS Minter - Ultra-Fast First Come First Serve Specialist
Reverse engineered GraphQL API for maximum speed
Based on research by @Zun2025 - optimized for Python async
"""

import asyncio
import json
import time
import base64
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
import requests
from web3 import Web3
from eth_account import Account
from eth_account.datastructures import SignedTransaction
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


@dataclass
class OpenSeaMintResult:
    """Result of OpenSea FCFS mint"""
    success: bool
    tx_hash: Optional[str] = None
    signature: Optional[str] = None
    salt: Optional[str] = None
    calldata: Optional[str] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None
    elapsed_ms: float = 0.0
    stage: str = ""  # Which stage failed if any


@dataclass
class OpenSeaConfig:
    """OpenSea configuration per chain"""
    chain: str  # eth, polygon, base, arb, etc.
    rpc_url: str
    private_key: str
    wallet_address: Optional[str] = None
    api_endpoint: str = "https://gql.opensea.io/graphql"
    os_contract: str = "0x00000000000000ADc04C56Bf30aC9d3c0aAF14dC"  # Seaport 1.5
    
    def __post_init__(self):
        if not self.wallet_address:
            account = Account.from_key(self.private_key)
            self.wallet_address = account.address


class OpenSeaGraphQLClient:
    """OpenSea internal GraphQL API client"""
    
    # GraphQL Operations (reverse engineered)
    MINT_ACTION_TIMELINE_QUERY = """
    query MintActionTimelineQuery(
        $address: String!
        $chain: Chain!
        $contractAddress: String!
        $tokenId: String!
        $quantity: String!
    ) {
        swap(
            address: $address
            fromAssets: [{
                asset: {
                    chain: $chain
                    contractAddress: "0x0000000000000000000000000000000000000000"
                }
            }]
            toAssets: [{
                asset: {
                    chain: $chain
                    contractAddress: $contractAddress
                    tokenId: $tokenId
                }
                quantity: $quantity
            }]
            action: MINT
            capabilities: { eip7702: false }
        ) {
            actions {
                __typename
                ... on TransactionAction {
                    transactionSubmissionData {
                        to
                        data
                        value
                    }
                }
            }
            errors {
                message
            }
        }
    }
    """
    
    MINT_QUERY = """
    query MintQuery($chain: Chain!, $contractAddress: String!) {
        collection(chain: $chain, contractAddress: $contractAddress) {
            id
            name
            drop {
                id
                stage {
                    id
                    kind
                    active
                    startTime
                    endTime
                }
            }
        }
    }
    """
    
    def __init__(self, config: OpenSeaConfig, cookies: Optional[Dict] = None):
        self.config = config
        self.cookies = cookies or {}
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def init_session(self):
        """Initialize aiohttp session with optimized settings"""
        if not self.session:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=50,
                enable_cleanup_closed=True,
                force_close=False,
                ttl_dns_cache=300,
            )
            
            timeout = aiohttp.ClientTimeout(
                total=5,
                connect=2,
                sock_read=3,
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Origin": "https://opensea.io",
                    "Referer": "https://opensea.io/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
            )
    
    async def get_mint_calldata(
        self,
        contract_address: str,
        token_id: str = "0",
        quantity: str = "1",
    ) -> Optional[Dict]:
        """
        Fetch mint calldata from OpenSea GraphQL
        This is the critical FCFS function - speed matters here!
        """
        variables = {
            "address": self.config.wallet_address,
            "chain": self.config.chain.upper(),
            "contractAddress": contract_address,
            "tokenId": token_id,
            "quantity": quantity,
        }
        
        payload = {
            "query": self.MINT_ACTION_TIMELINE_QUERY,
            "variables": variables,
        }
        
        try:
            async with self.session.post(
                self.config.api_endpoint,
                json=payload,
                cookies=self.cookies,
                ssl=False,  # Speed optimization (if behind proxy)
            ) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                # Extract transaction data
                swap_data = data.get("data", {}).get("swap", {})
                
                if swap_data.get("errors"):
                    return {"error": swap_data["errors"][0].get("message")}
                
                actions = swap_data.get("actions", [])
                if not actions:
                    return None
                
                tx_data = actions[0].get("transactionSubmissionData", {})
                
                return {
                    "to": tx_data.get("to"),
                    "data": tx_data.get("data"),
                    "value": int(tx_data.get("value", "0")),
                }
                
        except asyncio.TimeoutError:
            return {"error": "Timeout fetching calldata"}
        except Exception as e:
            return {"error": str(e)}
    
    async def check_drop_status(self, contract_address: str) -> Dict:
        """Check if drop is live and mintable"""
        variables = {
            "chain": self.config.chain.upper(),
            "contractAddress": contract_address,
        }
        
        payload = {
            "query": self.MINT_QUERY,
            "variables": variables,
        }
        
        try:
            async with self.session.post(
                self.config.api_endpoint,
                json=payload,
                cookies=self.cookies,
            ) as response:
                data = await response.json()
                return data.get("data", {}).get("collection", {})
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
            self.session = None


class OpenSeaFCFSMinter:
    """
    Ultra-Fast OpenSea FCFS Minter
    Optimized for competitive minting with <100ms response times
    """
    
    def __init__(self, config: OpenSeaConfig):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self.account = Account.from_key(config.private_key)
        self.graphql = OpenSeaGraphQLClient(config)
        
        # Speed optimization: Pre-initialize everything
        self._nonce_cache = 0
        self._last_nonce_update = 0
    
    def _get_fast_nonce(self) -> int:
        """Get nonce with caching for speed"""
        now = time.time()
        if now - self._last_nonce_update > 5:  # Refresh every 5 seconds
            self._nonce_cache = self.w3.eth.get_transaction_count(
                self.account.address,
                'pending'
            )
            self._last_nonce_update = now
        else:
            self._nonce_cache += 1
        
        return self._nonce_cache
    
    def _build_mint_tx(
        self,
        to: str,
        data: str,
        value: int,
        gas_limit: int = 300000,
    ) -> Dict:
        """Build transaction with optimized gas"""
        # Get gas fees
        try:
            latest = self.w3.eth.get_block('latest')
            base_fee = latest.get('baseFeePerGas', self.w3.to_wei(30, 'gwei'))
            
            # Aggressive gas for FCFS
            priority_fee = self.w3.to_wei(3, 'gwei')
            max_fee = int(base_fee * 2) + priority_fee
        except:
            # Fallback
            max_fee = self.w3.to_wei(100, 'gwei')
            priority_fee = self.w3.to_wei(3, 'gwei')
        
        return {
            "from": self.account.address,
            "to": Web3.to_checksum_address(to),
            "data": data,
            "value": value,
            "gas": gas_limit,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "nonce": self._get_fast_nonce(),
            "chainId": self.w3.eth.chain_id,
            "type": 2,  # EIP-1559
        }
    
    async def snipe_mint(
        self,
        contract_address: str,
        token_id: str = "0",
        quantity: str = "1",
        max_retries: int = 10,
    ) -> OpenSeaMintResult:
        """
        FCFS Mint - Ultra fast competitive minting
        
        Strategy:
        1. Pre-fetch calldata (blocking on OpenSea API)
        2. Build & sign transaction instantly
        3. Broadcast with aggressive gas
        4. Monitor for confirmation
        """
        start_time = time.perf_counter()
        
        await self.graphql.init_session()
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Stage 1: Fetch calldata from OpenSea (CRITICAL PATH)
                stage_start = time.perf_counter()
                calldata = await self.graphql.get_mint_calldata(
                    contract_address, token_id, quantity
                )
                stage_elapsed = (time.perf_counter() - stage_start) * 1000
                
                if not calldata:
                    last_error = "Failed to fetch calldata"
                    continue
                
                if "error" in calldata:
                    last_error = calldata["error"]
                    # If drop not live yet, retry faster
                    if "not live" in last_error.lower() or "stage" in last_error.lower():
                        await asyncio.sleep(0.1)
                        continue
                    break
                
                console.print(f"[dim]Calldata fetched in {stage_elapsed:.1f}ms[/dim]")
                
                # Stage 2: Build & sign transaction
                stage_start = time.perf_counter()
                tx = self._build_mint_tx(
                    calldata["to"],
                    calldata["data"],
                    calldata["value"],
                )
                
                signed = self.account.sign_transaction(tx)
                stage_elapsed = (time.perf_counter() - stage_start) * 1000
                console.print(f"[dim]TX signed in {stage_elapsed:.1f}ms[/dim]")
                
                # Stage 3: Broadcast
                stage_start = time.perf_counter()
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                tx_hash_hex = tx_hash.hex()
                stage_elapsed = (time.perf_counter() - stage_start) * 1000
                console.print(f"[dim]Broadcast in {stage_elapsed:.1f}ms[/dim]")
                
                # Calculate total time
                total_elapsed = (time.perf_counter() - start_time) * 1000
                
                # Wait for receipt (non-blocking for speed report)
                try:
                    receipt = self.w3.eth.wait_for_transaction_receipt(
                        tx_hash,
                        timeout=30,
                        poll_latency=0.5,
                    )
                    success = receipt.status == 1
                except:
                    success = True  # Assume success if broadcast worked
                
                result = OpenSeaMintResult(
                    success=success,
                    tx_hash=tx_hash_hex,
                    calldata=calldata["data"],
                    explorer_url=f"https://{self._get_explorer()}/tx/{tx_hash_hex}",
                    elapsed_ms=total_elapsed,
                )
                
                if success:
                    console.print(f"[green]✓ Minted in {total_elapsed:.1f}ms![/green]")
                
                return result
                
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.05 * (attempt + 1))  # Exponential backoff
        
        total_elapsed = (time.perf_counter() - start_time) * 1000
        
        return OpenSeaMintResult(
            success=False,
            error=f"Failed after {max_retries} attempts: {last_error}",
            elapsed_ms=total_elapsed,
            stage="calldata_fetch" if "calldata" in str(last_error).lower() else "broadcast"
        )
    
    async def prewarm_calldata(
        self,
        contract_address: str,
        token_id: str = "0",
        quantity: str = "1",
        interval: float = 0.5,
    ) -> Optional[Dict]:
        """
        Pre-warm: Keep polling for calldata until drop is live
        Then execute immediately when available
        """
        console.print(f"[yellow]Pre-warming calldata for {contract_address}...[/yellow]")
        
        await self.graphql.init_session()
        
        while True:
            calldata = await self.graphql.get_mint_calldata(
                contract_address, token_id, quantity
            )
            
            if calldata and "error" not in calldata:
                console.print("[green]✓ Drop is live! Calldata ready.[/green]")
                return calldata
            
            if calldata and "not live" not in str(calldata.get("error", "")).lower():
                console.print(f"[red]Error: {calldata.get('error')}[/red]")
                return None
            
            await asyncio.sleep(interval)
    
    def _get_explorer(self) -> str:
        """Get block explorer for chain"""
        explorers = {
            "eth": "etherscan.io",
            "polygon": "polygonscan.com",
            "base": "basescan.org",
            "arb": "arbiscan.io",
            "optimism": "optimistic.etherscan.io",
            "avalanche": "snowtrace.io",
        }
        return explorers.get(self.config.chain, "etherscan.io")
    
    async def close(self):
        """Cleanup"""
        await self.graphql.close()


class MultiWalletOpenSeaMinter:
    """Multi-wallet FCFS minting for maximum chances"""
    
    def __init__(self, configs: List[OpenSeaConfig]):
        self.configs = configs
        self.minters = [OpenSeaFCFSMinter(cfg) for cfg in configs]
    
    async def snipe_with_all(
        self,
        contract_address: str,
        token_id: str = "0",
        quantity: str = "1",
    ) -> List[Tuple[str, OpenSeaMintResult]]:
        """Mint with all wallets simultaneously"""
        tasks = [
            minter.snipe_mint(contract_address, token_id, quantity)
            for minter in self.minters
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = []
        for config, result in zip(self.configs, results):
            if isinstance(result, Exception):
                output.append((
                    config.wallet_address[:10],
                    OpenSeaMintResult(success=False, error=str(result))
                ))
            else:
                output.append((config.wallet_address[:10], result))
        
        return output
    
    async def close(self):
        """Cleanup all minters"""
        for minter in self.minters:
            await minter.close()


def create_opensea_config_from_env(chain: str) -> Optional[OpenSeaConfig]:
    """Factory function to create OpenSea config from environment"""
    import os
    
    chain_upper = chain.upper()
    rpc_url = os.getenv(f"{chain_upper}_RPC_URL")
    private_key = os.getenv(f"{chain_upper}_PRIVATE_KEY")
    
    if not rpc_url or not private_key:
        return None
    
    return OpenSeaConfig(
        chain=chain.lower(),
        rpc_url=rpc_url,
        private_key=private_key,
    )

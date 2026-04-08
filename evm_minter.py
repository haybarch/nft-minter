"""
EVM Minter - Super Fast NFT Minting for EVM Chains
Supports: Ethereum, Arbitrum, Base, Polygon, Optimism, Avalanche, BSC, and more
"""

import time
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3, AsyncWeb3
from web3.types import TxParams, Wei
from eth_account import Account
from eth_account.datastructures import SignedTransaction
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests

console = Console()


@dataclass
class MintResult:
    """Result of mint transaction"""
    success: bool
    tx_hash: Optional[str] = None
    token_id: Optional[int] = None
    gas_used: Optional[int] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None


class GasStation:
    """Get optimal gas prices from various sources"""
    
    @staticmethod
    def get_eth_gasstation() -> Dict[str, int]:
        """Get gas from ETH Gas Station"""
        try:
            resp = requests.get("https://ethgasstation.info/api/ethgasAPI.json", timeout=5)
            data = resp.json()
            return {
                "fast": data.get("fast", 50),
                "standard": data.get("average", 30),
                "slow": data.get("safeLow", 20),
            }
        except Exception:
            return {}
    
    @staticmethod
    def estimate_gas_fees(w3: Web3, aggressive: bool = False) -> Dict[str, int]:
        """Estimate gas fees with optional aggressive pricing"""
        try:
            # Get latest block for base fee
            latest = w3.eth.get_block('latest')
            base_fee = latest.get('baseFeePerGas', w3.to_wei(20, 'gwei'))
            
            # Calculate priority fee
            if aggressive:
                # Aggressive: 95th percentile + 20%
                priority_fee = int(base_fee * 0.3)  # 30% of base fee
                max_fee = int(base_fee * 2.5)  # 2.5x base fee
            else:
                priority_fee = w3.to_wei(2, 'gwei')
                max_fee = int(base_fee * 1.5) + priority_fee
            
            return {
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
            }
        except Exception as e:
            console.print(f"[yellow]⚠ Gas estimation failed: {e}[/yellow]")
            # Fallback values
            return {
                "maxFeePerGas": w3.to_wei(50, 'gwei'),
                "maxPriorityFeePerGas": w3.to_wei(2, 'gwei'),
            }


class EVMMinter:
    """Super-fast EVM NFT Minter"""
    
    # Standard NFT contract ABI (ERC721)
    ERC721_ABI = [
        {
            "inputs": [],
            "name": "mint",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "quantity", "type": "uint256"}],
            "name": "mint",
            "outputs": [],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "to", "type": "address"}],
            "name": "mintTo",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
            "name": "ownerOf",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "price",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "maxPerWallet",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]
    
    def __init__(self, config):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self.account = Account.from_key(config.private_key)
        self.gas_station = GasStation()
        
        # Initialize contract if provided
        self.contract = None
        if config.nft_contract:
            self.set_contract(config.nft_contract)
    
    def set_contract(self, contract_address: str):
        """Set NFT contract address"""
        checksum_address = Web3.to_checksum_address(contract_address)
        self.contract = self.w3.eth.contract(
            address=checksum_address,
            abi=self.ERC721_ABI
        )
        console.print(f"[green]✓[/green] Contract set: {checksum_address}")
    
    def get_balance(self) -> Decimal:
        """Get wallet balance in ETH"""
        balance_wei = self.w3.eth.get_balance(self.account.address)
        return Decimal(self.w3.from_wei(balance_wei, 'ether'))
    
    def get_contract_info(self) -> Dict[str, Any]:
        """Get NFT contract information"""
        if not self.contract:
            return {}
        
        info = {}
        try:
            info["totalSupply"] = self.contract.functions.totalSupply().call()
        except Exception:
            pass
        
        try:
            info["price"] = self.w3.from_wei(
                self.contract.functions.price().call(), 'ether'
            )
        except Exception:
            pass
        
        try:
            info["maxPerWallet"] = self.contract.functions.maxPerWallet().call()
        except Exception:
            pass
        
        try:
            info["balance"] = self.contract.functions.balanceOf(
                self.account.address
            ).call()
        except Exception:
            pass
        
        return info
    
    def build_mint_tx(
        self,
        quantity: int = 1,
        mint_price: Optional[int] = None,
        custom_data: Optional[str] = None,
        gas_override: Optional[Dict] = None,
    ) -> TxParams:
        """Build mint transaction"""
        
        # Get gas fees
        if gas_override:
            gas_fees = gas_override
        else:
            gas_fees = self.gas_station.estimate_gas_fees(
                self.w3, 
                aggressive=self.config.aggressive_gas
            )
        
        # Get nonce
        nonce = self.w3.eth.get_transaction_count(
            self.account.address,
            'pending'  # Use pending for fastest minting
        )
        
        # Build base transaction
        tx: TxParams = {
            "from": self.account.address,
            "nonce": nonce,
            "gas": self.config.gas_limit,
            "chainId": self.config.chain_id,
            **gas_fees,
        }
        
        # Add contract interaction if contract is set
        if self.contract:
            # Determine mint function
            mint_price = mint_price or 0
            value = mint_price * quantity
            
            try:
                # Try mint(uint256 quantity)
                tx = self.contract.functions.mint(quantity).build_transaction(tx)
            except Exception:
                try:
                    # Try mint() with no args
                    tx = self.contract.functions.mint().build_transaction(tx)
                except Exception:
                    # Try mintTo(address)
                    tx = self.contract.functions.mintTo(
                        self.account.address
                    ).build_transaction(tx)
            
            tx["value"] = value
        else:
            # Direct transaction with custom data
            if custom_data:
                tx["data"] = custom_data
            if mint_price:
                tx["value"] = mint_price
        
        return tx
    
    def send_transaction(
        self,
        tx: TxParams,
        timeout: int = 120,
    ) -> MintResult:
        """Sign and send transaction"""
        try:
            # Sign transaction
            signed: SignedTransaction = self.account.sign_transaction(tx)
            
            # Send raw transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=timeout,
            )
            
            # Build result
            result = MintResult(
                success=receipt.status == 1,
                tx_hash=tx_hash_hex,
                gas_used=receipt.gasUsed,
                explorer_url=f"{self.config.explorer}{tx_hash_hex}" if self.config.explorer else None,
            )
            
            return result
            
        except Exception as e:
            return MintResult(
                success=False,
                error=str(e),
            )
    
    def mint(
        self,
        quantity: int = 1,
        mint_price_eth: Optional[float] = None,
        max_retries: int = 3,
        retry_delay: int = 1,
    ) -> MintResult:
        """
        Mint NFT with retry logic
        
        Args:
            quantity: Number of NFTs to mint
            mint_price_eth: Price per NFT in ETH
            max_retries: Max retry attempts
            retry_delay: Seconds between retries
        
        Returns:
            MintResult with transaction details
        """
        mint_price = None
        if mint_price_eth:
            mint_price = self.w3.to_wei(mint_price_eth, 'ether')
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Build transaction
                tx = self.build_mint_tx(quantity, mint_price)
                
                # Show attempt
                if attempt > 0:
                    console.print(f"[yellow]Retry {attempt}/{max_retries}...[/yellow]")
                
                # Send with progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        f"[cyan]Minting on {self.config.name.upper()}...",
                        total=None,
                    )
                    
                    result = self.send_transaction(tx, timeout=self.config.tx_timeout)
                    progress.stop()
                
                if result.success:
                    console.print(f"[green]✓[/green] Minted! TX: {result.tx_hash[:20]}...")
                    if result.explorer_url:
                        console.print(f"  [dim]{result.explorer_url}[/dim]")
                    return result
                else:
                    last_error = result.error
                    console.print(f"[red]✗[/red] Failed: {result.error}")
                    
            except Exception as e:
                last_error = str(e)
                console.print(f"[red]✗[/red] Error: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        return MintResult(
            success=False,
            error=f"Failed after {max_retries} attempts: {last_error}",
        )
    
    async def mint_async(
        self,
        quantity: int = 1,
        mint_price_eth: Optional[float] = None,
    ) -> MintResult:
        """Async mint for concurrent operations"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.mint,
            quantity,
            mint_price_eth,
        )
    
    def mint_multiple_chains(
        self,
        chains: List[Any],
        quantity: int = 1,
        mint_price_eth: Optional[float] = None,
    ) -> Dict[str, MintResult]:
        """Mint on multiple chains concurrently"""
        results = {}
        
        def mint_on_chain(chain_config):
            minter = EVMMinter(chain_config)
            if chain_config.nft_contract:
                return chain_config.name, minter.mint(quantity, mint_price_eth)
            return chain_config.name, MintResult(
                success=False,
                error="No contract configured"
            )
        
        # Use ThreadPoolExecutor for concurrent minting
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=len(chains)) as executor:
            futures = {
                executor.submit(mint_on_chain, chain): chain 
                for chain in chains
            }
            
            for future in as_completed(futures):
                chain_name, result = future.result()
                results[chain_name] = result
        
        return results

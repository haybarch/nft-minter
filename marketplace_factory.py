#!/usr/bin/env python3
"""
Universal NFT Marketplace Factory
Unified interface for OpenSea, Magic Eden, Tensor, Blur, and direct minting
"""

import asyncio
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum
from rich.console import Console

from evm_minter import EVMMinter, EVMChainConfig, MintResult
from solana_minter import SolanaMinter, SolanaConfig, SolanaMintResult
from opensea_minter import (
    OpenSeaFCFSMinter, OpenSeaConfig, OpenSeaMintResult,
    create_opensea_config_from_env
)

console = Console()


class MarketplaceType(Enum):
    """Supported marketplaces"""
    OPENSEA = "opensea"
    MAGIC_EDEN = "magic_eden"
    TENSOR = "tensor"
    BLUR = "blur"
    LOOKSRARE = "looksrare"
    DIRECT_EVM = "direct_evm"
    DIRECT_SOLANA = "direct_solana"


@dataclass
class MintRequest:
    """Universal mint request"""
    marketplace: MarketplaceType
    chain: str
    contract_address: str
    token_id: Optional[str] = None
    quantity: int = 1
    price: Optional[float] = None
    wallet_index: int = 0  # For multi-wallet


@dataclass
class MintResponse:
    """Universal mint response"""
    success: bool
    marketplace: str
    chain: str
    tx_hash: Optional[str] = None
    token_address: Optional[str] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None
    elapsed_ms: float = 0.0
    metadata: Dict[str, Any] = None


class BaseMarketplaceMinter:
    """Base class for all marketplace minters"""
    
    async def mint(self, request: MintRequest) -> MintResponse:
        """Execute mint - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def check_status(self, contract_address: str) -> Dict[str, Any]:
        """Check drop/mint status"""
        raise NotImplementedError
    
    async def close(self):
        """Cleanup resources"""
        pass


class MagicEdenMinter(BaseMarketplaceMinter):
    """
    Magic Eden Minter
    Supports both EVM and Solana chains
    """
    
    API_BASE = {
        "solana": "https://api-mainnet.magiceden.dev/v2",
        "eth": "https://api-mainnet.magiceden.io/v3",
        "polygon": "https://api-mainnet.magiceden.io/v3",
    }
    
    def __init__(self, chain: str, config: Union[EVMChainConfig, SolanaConfig]):
        self.chain = chain
        self.config = config
        self.is_evm = isinstance(config, EVMChainConfig)
        
        if self.is_evm:
            self.evm_minter = EVMMinter(config)
    
    async def mint(self, request: MintRequest) -> MintResponse:
        """Mint on Magic Eden"""
        # Magic Eden minting typically uses direct contract calls
        # with their specific forwarding contract
        
        if self.is_evm:
            # Use direct mint with Magic Eden forwarding
            result = self.evm_minter.mint(
                quantity=request.quantity,
                mint_price_eth=request.price,
            )
            
            return MintResponse(
                success=result.success,
                marketplace="magic_eden",
                chain=self.chain,
                tx_hash=result.tx_hash,
                error=result.error,
                explorer_url=result.explorer_url,
            )
        else:
            # Solana - use direct Solana minter
            sol_minter = SolanaMinter(self.config)
            result = await sol_minter.mint_async(
                candy_machine_id=request.contract_address
            )
            
            return MintResponse(
                success=result.success,
                marketplace="magic_eden",
                chain=self.chain,
                tx_hash=result.signature,
                token_address=result.token_address,
                error=result.error,
                explorer_url=result.explorer_url,
            )
    
    async def check_status(self, contract_address: str) -> Dict[str, Any]:
        """Check Magic Eden drop status"""
        import aiohttp
        
        base_url = self.API_BASE.get(self.chain, self.API_BASE["eth"])
        
        async with aiohttp.ClientSession() as session:
            # Collection stats endpoint
            url = f"{base_url}/collections/{contract_address}/stats"
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "floor_price": data.get("floorPrice"),
                            "listed_count": data.get("listedCount"),
                            "total_volume": data.get("volumeAll"),
                        }
                    return {"error": f"Status {resp.status}"}
            except Exception as e:
                return {"error": str(e)}


class TensorMinter(BaseMarketplaceMinter):
    """
    Tensor (Solana NFT marketplace) Minter
    Fast Solana NFT trading with aggressive execution
    """
    
    API_BASE = "https://api.tensor.so/graphql"
    
    def __init__(self, config: SolanaConfig):
        self.config = config
        self.solana_minter = SolanaMinter(config)
    
    async def mint(self, request: MintRequest) -> MintResponse:
        """Mint on Tensor"""
        # Tensor uses standard Candy Machine / Metaplex
        # but with their optimized transaction batching
        
        result = await self.solana_minter.mint_async(
            candy_machine_id=request.contract_address
        )
        
        return MintResponse(
            success=result.success,
            marketplace="tensor",
            chain="solana",
            tx_hash=result.signature,
            token_address=result.token_address,
            error=result.error,
            explorer_url=f"https://solscan.io/tx/{result.signature}" if result.signature else None,
        )
    
    async def check_status(self, contract_address: str) -> Dict[str, Any]:
        """Check Tensor collection status"""
        # Tensor uses GraphQL - simplified check
        return {"status": "unknown", "note": "Use Tensor UI for detailed status"}


class BlurMinter(BaseMarketplaceMinter):
    """
    Blur (Ethereum NFT marketplace) Minter
    Focused on pro traders with bulk operations
    """
    
    API_BASE = "https://api.blur.io/v1"
    
    def __init__(self, config: EVMChainConfig):
        self.config = config
        self.evm_minter = EVMMinter(config)
    
    async def mint(self, request: MintRequest) -> MintResponse:
        """Mint on Blur"""
        # Blur minting typically goes through their marketplace contract
        result = self.evm_minter.mint(
            quantity=request.quantity,
            mint_price_eth=request.price,
        )
        
        return MintResponse(
            success=result.success,
            marketplace="blur",
            chain=self.config.name,
            tx_hash=result.tx_hash,
            error=result.error,
            explorer_url=result.explorer_url,
        )
    
    async def check_status(self, contract_address: str) -> Dict[str, Any]:
        """Check Blur collection status"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.API_BASE}/collections/{contract_address}"
            try:
                async with session.get(url, timeout=5) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"error": f"Status {resp.status}"}
            except Exception as e:
                return {"error": str(e)}


class UniversalMinterFactory:
    """
    Factory for creating marketplace minters
    Single entry point for all NFT minting operations
    """
    
    def __init__(self):
        self._minters: Dict[str, BaseMarketplaceMinter] = {}
        self._configs: Dict[str, Any] = {}
    
    def register_config(
        self,
        marketplace: MarketplaceType,
        chain: str,
        config: Union[EVMChainConfig, SolanaConfig, OpenSeaConfig]
    ):
        """Register configuration for a marketplace-chain pair"""
        key = f"{marketplace.value}_{chain}"
        self._configs[key] = config
    
    def create_minter(
        self,
        marketplace: MarketplaceType,
        chain: str,
    ) -> Optional[BaseMarketplaceMinter]:
        """Create minter instance for marketplace and chain"""
        key = f"{marketplace.value}_{chain}"
        config = self._configs.get(key)
        
        if not config:
            return None
        
        if marketplace == MarketplaceType.OPENSEA:
            return OpenSeaFCFSMinter(config)
        elif marketplace == MarketplaceType.MAGIC_EDEN:
            return MagicEdenMinter(chain, config)
        elif marketplace == MarketplaceType.TENSOR:
            return TensorMinter(config)
        elif marketplace == MarketplaceType.BLUR:
            return MagicEdenMinter(chain, config)  # Blur is EVM
        elif marketplace == MarketplaceType.DIRECT_EVM:
            return self._wrap_evm_minter(config)
        elif marketplace == MarketplaceType.DIRECT_SOLANA:
            return self._wrap_solana_minter(config)
        
        return None
    
    def _wrap_evm_minter(self, config: EVMChainConfig) -> BaseMarketplaceMinter:
        """Wrap EVM minter in marketplace interface"""
        class WrappedEVMMinter(BaseMarketplaceMinter):
            def __init__(self, config):
                self.minter = EVMMinter(config)
                self.chain = config.name
            
            async def mint(self, request: MintRequest) -> MintResponse:
                result = self.minter.mint(
                    quantity=request.quantity,
                    mint_price_eth=request.price,
                )
                return MintResponse(
                    success=result.success,
                    marketplace="direct_evm",
                    chain=self.chain,
                    tx_hash=result.tx_hash,
                    error=result.error,
                    explorer_url=result.explorer_url,
                )
            
            async def check_status(self, contract_address: str) -> Dict[str, Any]:
                try:
                    info = self.minter.get_contract_info()
                    return info
                except Exception as e:
                    return {"error": str(e)}
        
        return WrappedEVMMinter(config)
    
    def _wrap_solana_minter(self, config: SolanaConfig) -> BaseMarketplaceMinter:
        """Wrap Solana minter in marketplace interface"""
        class WrappedSolanaMinter(BaseMarketplaceMinter):
            def __init__(self, config):
                self.minter = SolanaMinter(config)
            
            async def mint(self, request: MintRequest) -> MintResponse:
                result = await self.minter.mint_async(
                    candy_machine_id=request.contract_address
                )
                return MintResponse(
                    success=result.success,
                    marketplace="direct_solana",
                    chain="solana",
                    tx_hash=result.signature,
                    token_address=result.token_address,
                    error=result.error,
                    explorer_url=result.explorer_url,
                )
            
            async def check_status(self, contract_address: str) -> Dict[str, Any]:
                return self.minter.check_candy_machine_state(contract_address)
        
        return WrappedSolanaMinter(config)
    
    async def execute_mint(self, request: MintRequest) -> MintResponse:
        """Execute mint across any marketplace"""
        minter = self.create_minter(request.marketplace, request.chain)
        
        if not minter:
            return MintResponse(
                success=False,
                marketplace=request.marketplace.value,
                chain=request.chain,
                error=f"No minter configured for {request.marketplace.value} on {request.chain}"
            )
        
        try:
            return await minter.mint(request)
        finally:
            await minter.close()
    
    def get_supported_marketplaces(self) -> List[str]:
        """Get list of configured marketplaces"""
        return list(set(k.split("_")[0] for k in self._configs.keys()))
    
    def get_supported_chains(self, marketplace: MarketplaceType) -> List[str]:
        """Get supported chains for a marketplace"""
        prefix = marketplace.value
        return [k.replace(f"{prefix}_", "") for k in self._configs.keys() if k.startswith(prefix)]


# Convenience functions
async def mint_opensea_fcfs(
    chain: str,
    contract_address: str,
    token_id: str = "0",
    quantity: str = "1",
    cookies: Optional[Dict] = None,
) -> OpenSeaMintResult:
    """
    Quick function for OpenSea FCFS minting
    
    Usage:
        result = await mint_opensea_fcfs(
            chain="base",
            contract_address="0x...",
            token_id="0",
        )
    """
    config = create_opensea_config_from_env(chain)
    if not config:
        return OpenSeaMintResult(
            success=False,
            error=f"No OpenSea config found for {chain}. Check .env"
        )
    
    if cookies:
        config.cookies = cookies
    
    minter = OpenSeaFCFSMinter(config)
    
    try:
        return await minter.snipe_mint(contract_address, token_id, quantity)
    finally:
        await minter.close()


async def mint_universal(
    marketplace: str,
    chain: str,
    contract_address: str,
    **kwargs
) -> MintResponse:
    """
    Universal mint function - works with any marketplace
    
    Usage:
        result = await mint_universal(
            marketplace="opensea",
            chain="base",
            contract_address="0x...",
            quantity=1,
        )
    """
    try:
        mp_type = MarketplaceType(marketplace.lower())
    except ValueError:
        return MintResponse(
            success=False,
            marketplace=marketplace,
            chain=chain,
            error=f"Unknown marketplace: {marketplace}"
        )
    
    request = MintRequest(
        marketplace=mp_type,
        chain=chain,
        contract_address=contract_address,
        **kwargs
    )
    
    factory = UniversalMinterFactory()
    # TODO: Load configs from environment
    
    return await factory.execute_mint(request)

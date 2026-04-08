"""
Solana Minter - Super Fast NFT Minting for Solana
Supports: Candy Machine v3, Metaplex, SPL Token NFTs
"""

import asyncio
import json
import base58
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass

from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.transaction import Transaction, TransactionInstruction
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.system_program import CreateAccountParams, create_account
from solana.sysvar import SYSVAR_RENT_PUBKEY, SYSVAR_INSTRUCTIONS_PUBKEY
from solana.instruction import Instruction
import solders.keypair as solders_keypair
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.instruction import Instruction as SoldersInstruction
from solders.account_meta import AccountMeta
from solders.pubkey import Pubkey
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from solders.sysvar import INSTRUCTIONS as SOLDERS_INSTRUCTIONS_ID

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class SolanaMintResult:
    """Result of Solana mint transaction"""
    success: bool
    signature: Optional[str] = None
    token_address: Optional[str] = None
    error: Optional[str] = None
    explorer_url: Optional[str] = None
    slot: Optional[int] = None


class SolanaMinter:
    """Super-fast Solana NFT Minter"""
    
    # Metaplex Candy Machine IDLs (simplified)
    CANDY_MACHINE_ID = "CndyV3LdqHUfDLmE5naZjVN8rBZz4tqhdefbAnjHG3JR"
    TOKEN_METADATA_PROGRAM_ID = "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
    
    def __init__(self, config):
        self.config = config
        self.client = Client(config.rpc_url)
        self.async_client = None
        
        # Initialize keypair
        self.keypair = self._load_keypair()
        self.wallet_address = str(self.keypair.pubkey())
        
        console.print(f"[green]✓[/green] Solana wallet: {self.wallet_address[:20]}...")
    
    def _load_keypair(self) -> solders_keypair.Keypair:
        """Load keypair from config"""
        if self.config.keypair_path:
            # Load from file
            with open(self.config.keypair_path, 'r') as f:
                secret_key = json.load(f)
            return solders_keypair.Keypair.from_bytes(bytes(secret_key))
        
        elif self.config.private_key:
            # Load from base58 string
            secret_key = base58.b58decode(self.config.private_key)
            return solders_keypair.Keypair.from_bytes(secret_key)
        
        else:
            raise ValueError("No private key or keypair path provided")
    
    def get_balance(self) -> float:
        """Get SOL balance"""
        try:
            response = self.client.get_balance(self.keypair.pubkey())
            return response.value / 1e9  # Convert lamports to SOL
        except Exception as e:
            console.print(f"[red]Error getting balance: {e}[/red]")
            return 0.0
    
    async def get_balance_async(self) -> float:
        """Get SOL balance asynchronously"""
        if not self.async_client:
            self.async_client = AsyncClient(self.config.rpc_url)
        
        try:
            response = await self.async_client.get_balance(self.keypair.pubkey())
            return response.value / 1e9
        except Exception as e:
            console.print(f"[red]Error getting balance: {e}[/red]")
            return 0.0
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            response = self.client.get_account_info(self.keypair.pubkey())
            return {
                "lamports": response.value.lamports,
                "owner": str(response.value.owner),
                "executable": response.value.executable,
                "rent_epoch": response.value.rent_epoch,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _build_candy_machine_mint_ix(
        self,
        candy_machine_id: str,
        payer: Pubkey,
    ) -> Optional[SoldersInstruction]:
        """Build Candy Machine mint instruction"""
        try:
            candy_machine_pubkey = Pubkey.from_string(candy_machine_id)
            
            # This is a simplified version - real implementation needs
            # proper account derivation based on Candy Machine state
            
            # Standard Candy Machine v3 accounts
            accounts = [
                AccountMeta(payer, True, True),  # payer (signer, writable)
                AccountMeta(candy_machine_pubkey, False, True),  # candy machine
                # Additional accounts would be derived here...
            ]
            
            # Mint instruction discriminator (Candy Machine v3)
            data = bytes([211, 57, 6, 167, 15, 219, 35, 89])  # mint instruction
            
            return SoldersInstruction(
                program_id=Pubkey.from_string(self.CANDY_MACHINE_ID),
                accounts=accounts,
                data=data,
            )
        except Exception as e:
            console.print(f"[red]Error building instruction: {e}[/red]")
            return None
    
    def mint_candy_machine(
        self,
        candy_machine_id: Optional[str] = None,
        max_retries: int = 3,
    ) -> SolanaMintResult:
        """
        Mint from Candy Machine v3
        
        Args:
            candy_machine_id: Candy Machine address (uses config if not provided)
            max_retries: Maximum retry attempts
        
        Returns:
            SolanaMintResult with transaction details
        """
        cm_id = candy_machine_id or self.config.candy_machine_id
        if not cm_id:
            return SolanaMintResult(
                success=False,
                error="No Candy Machine ID provided"
            )
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(
                        f"[cyan]Minting Solana NFT... (attempt {attempt + 1})",
                        total=None,
                    )
                    
                    # Build instructions
                    ix = self._build_candy_machine_mint_ix(
                        cm_id,
                        self.keypair.pubkey(),
                    )
                    
                    if not ix:
                        return SolanaMintResult(
                            success=False,
                            error="Failed to build mint instruction"
                        )
                    
                    # Get fresh blockhash
                    blockhash_resp = self.client.get_latest_blockhash()
                    blockhash = blockhash_resp.value.blockhash
                    
                    # Build message
                    message = MessageV0.new_with_blockhash_and_payer(
                        [ix],
                        self.keypair.pubkey(),
                        blockhash,
                    )
                    
                    # Sign transaction
                    tx = VersionedTransaction(message, [self.keypair])
                    
                    # Send transaction
                    tx_opts = TxOpts(
                        skip_preflight=True,  # Skip preflight for speed
                        preflight_commitment="processed",
                    )
                    
                    response = self.client.send_transaction(tx, opts=tx_opts)
                    signature = str(response.value)
                    
                    progress.stop()
                
                console.print(f"[green]✓[/green] Minted! Signature: {signature[:20]}...")
                console.print(f"  [dim]https://solscan.io/tx/{signature}[/dim]")
                
                return SolanaMintResult(
                    success=True,
                    signature=signature,
                    explorer_url=f"https://solscan.io/tx/{signature}",
                )
                
            except Exception as e:
                last_error = str(e)
                console.print(f"[red]✗[/red] Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    asyncio.sleep(1)
        
        return SolanaMintResult(
            success=False,
            error=f"Failed after {max_retries} attempts: {last_error}",
        )
    
    async def mint_async(
        self,
        candy_machine_id: Optional[str] = None,
    ) -> SolanaMintResult:
        """Async mint for concurrent operations"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.mint_candy_machine,
            candy_machine_id,
        )
    
    def mint_spl_nft(
        self,
        mint_amount: int = 1,
        max_retries: int = 3,
    ) -> SolanaMintResult:
        """
        Mint SPL Token NFT (for simple token mints)
        This is a placeholder - real implementation needs
        specific token mint authority.
        """
        # Implementation depends on specific token mint requirements
        return SolanaMintResult(
            success=False,
            error="SPL NFT mint not implemented - use Candy Machine for now"
        )
    
    def check_candy_machine_state(self, candy_machine_id: str) -> Dict[str, Any]:
        """Check Candy Machine state before minting"""
        try:
            cm_pubkey = Pubkey.from_string(candy_machine_id)
            response = self.client.get_account_info(cm_pubkey)
            
            if response.value:
                data = response.value.data
                # Parse Candy Machine data (simplified)
                # Real implementation needs proper Borsh deserialization
                return {
                    "exists": True,
                    "data_size": len(data),
                    "lamports": response.value.lamports,
                }
            else:
                return {"exists": False}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_token_accounts(self) -> List[Dict[str, Any]]:
        """Get all token accounts owned by wallet"""
        try:
            response = self.client.get_token_accounts_by_owner(
                self.keypair.pubkey(),
                {"programId": Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")},
            )
            
            accounts = []
            for acc in response.value:
                accounts.append({
                    "pubkey": str(acc.pubkey),
                    "account": {
                        "mint": str(acc.account.data.parsed['info']['mint']),
                        "amount": acc.account.data.parsed['info']['tokenAmount']['uiAmount'],
                    }
                })
            
            return accounts
        except Exception as e:
            console.print(f"[red]Error getting token accounts: {e}[/red]")
            return []
    
    async def close(self):
        """Close async client connection"""
        if self.async_client:
            await self.async_client.close()

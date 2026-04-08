#!/usr/bin/env python3
"""
OpenSea Auto Auth - Headless Browser Auth Token Fetcher
Automatically login to OpenSea and extract auth cookies
"""

import os
import json
import time
from typing import Optional, Dict
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


class OpenSeaAutoAuth:
    """Automated OpenSea authentication using headless browser"""
    
    def __init__(self):
        load_dotenv()
        self.env_file = ".env"
        self.cookies: Dict[str, str] = {}
        
    def try_playwright_auth(
        self,
        wallet_private_key: Optional[str] = None,
        headless: bool = True,
    ) -> bool:
        """
        Try to authenticate using Playwright browser automation
        Requires: pip install playwright
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with console.status("[cyan]Starting browser automation...[/cyan]"):
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=headless)
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )
                    
                    page = context.new_page()
                    
                    # Navigate to OpenSea
                    console.print("[yellow]Navigating to OpenSea...[/yellow]")
                    page.goto("https://opensea.io")
                    
                    # Wait for either login button or already logged in state
                    try:
                        # Check if already logged in
                        page.wait_for_selector("[data-testid='AccountDropdown']", timeout=5000)
                        console.print("[green]✓ Already logged in![/green]")
                    except:
                        # Need to login
                        console.print("[yellow]Please login manually in the browser window...[/yellow]")
                        console.print("[dim]The browser will stay open for 60 seconds[/dim]")
                        
                        # Open login modal
                        login_btn = page.locator("button:has-text('Connect wallet')").first
                        if login_btn.is_visible():
                            login_btn.click()
                        
                        # Wait for manual login
                        page.wait_for_selector("[data-testid='AccountDropdown']", timeout=60000)
                        console.print("[green]✓ Login successful![/green]")
                    
                    # Extract cookies
                    cookies = context.cookies()
                    
                    for cookie in cookies:
                        name = cookie.get("name", "")
                        value = cookie.get("value", "")
                        
                        if name in ["auth_token", "os_session", "session"]:
                            self.cookies["OPENSEA_AUTH_TOKEN"] = value
                        elif name == "csrftoken":
                            self.cookies["OPENSEA_CSRF_TOKEN"] = value
                    
                    browser.close()
                    
                    if self.cookies:
                        return True
                    else:
                        console.print("[red]✗ Could not extract auth cookies[/red]")
                        return False
                        
        except ImportError:
            console.print("[red]Playwright not installed. Run: pip install playwright[/red]")
            console.print("[yellow]Then: playwright install chromium[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    def try_selenium_auth(
        self,
        headless: bool = True,
    ) -> bool:
        """
        Alternative: Try Selenium browser automation
        Requires: pip install selenium webdriver-manager
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            with console.status("[cyan]Starting Selenium browser...[/cyan]"):
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                
                driver.get("https://opensea.io")
                
                # Wait for page load
                time.sleep(3)
                
                # Get cookies
                cookies = driver.get_cookies()
                
                for cookie in cookies:
                    name = cookie.get("name", "")
                    value = cookie.get("value", "")
                    
                    if name in ["auth_token", "os_session", "session"]:
                        self.cookies["OPENSEA_AUTH_TOKEN"] = value
                    elif name == "csrftoken":
                        self.cookies["OPENSEA_CSRF_TOKEN"] = value
                
                driver.quit()
                
                if self.cookies:
                    return True
                return False
                
        except ImportError:
            console.print("[red]Selenium not installed. Run: pip install selenium webdriver-manager[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Selenium error: {e}[/red]")
            return False
    
    def manual_cookie_input(self) -> bool:
        """Manual cookie input from user"""
        console.print("\n[bold cyan]Manual Cookie Input[/bold cyan]\n")
        console.print("1. Open https://opensea.io in your browser")
        console.print("2. Login with your wallet")
        console.print("3. Press F12 → Application → Cookies → https://opensea.io")
        console.print("4. Copy the values below:\n")
        
        auth_token = console.input("[yellow]auth_token (or os_session):[/yellow] ").strip()
        csrf_token = console.input("[yellow]csrftoken:[/yellow] ").strip()
        
        if auth_token:
            self.cookies["OPENSEA_AUTH_TOKEN"] = auth_token
        if csrf_token:
            self.cookies["OPENSEA_CSRF_TOKEN"] = csrf_token
        
        return bool(auth_token or csrf_token)
    
    def save_to_env(self) -> bool:
        """Save cookies to .env file"""
        if not self.cookies:
            return False
        
        try:
            # Read existing .env
            env_content = ""
            if os.path.exists(self.env_file):
                with open(self.env_file, "r") as f:
                    env_content = f.read()
            
            # Update or add cookie values
            for key, value in self.cookies.items():
                # Check if key already exists
                if f"{key}=" in env_content:
                    # Replace existing value
                    import re
                    env_content = re.sub(
                        f"{key}=.*",
                        f"{key}={value}",
                        env_content
                    )
                else:
                    # Add new line
                    env_content += f"\n{key}={value}\n"
            
            # Write back
            with open(self.env_file, "w") as f:
                f.write(env_content)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error saving to .env: {e}[/red]")
            return False
    
    def test_auth(self) -> bool:
        """Test if auth tokens work"""
        import requests
        
        auth_token = self.cookies.get("OPENSEA_AUTH_TOKEN", os.getenv("OPENSEA_AUTH_TOKEN", ""))
        
        if not auth_token:
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}" if not auth_token.startswith("Bearer") else auth_token,
                "Content-Type": "application/json",
            }
            
            # Test query
            response = requests.get(
                "https://api.opensea.io/api/v1/collections",
                headers=headers,
                params={"offset": 0, "limit": 1},
                timeout=10
            )
            
            if response.status_code == 200:
                console.print("[green]✓ Auth tokens are valid![/green]")
                return True
            else:
                console.print(f"[red]✗ Auth test failed: {response.status_code}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Auth test error: {e}[/red]")
            return False
    
    def run(self):
        """Main auth flow"""
        console.print(Panel.fit(
            "[bold cyan]OpenSea Auto Auth[/bold cyan]\n"
            "[dim]Fetch authentication tokens automatically[/dim]",
            border_style="cyan"
        ))
        
        # Check if already configured
        existing_auth = os.getenv("OPENSEA_AUTH_TOKEN")
        if existing_auth:
            console.print(f"[yellow]⚠️  OpenSea auth already configured[/yellow]")
            overwrite = console.input("Overwrite? [y/N]: ").lower() == 'y'
            if not overwrite:
                return
        
        # Try methods
        methods = [
            ("Playwright (Headless Browser)", self.try_playwright_auth),
            ("Selenium (Alternative)", self.try_selenium_auth),
            ("Manual Input", self.manual_cookie_input),
        ]
        
        success = False
        
        for method_name, method_fn in methods:
            console.print(f"\n[bold]Trying: {method_name}[/bold]")
            
            try:
                if method_fn():
                    success = True
                    console.print(f"[green]✓ Success with {method_name}[/green]")
                    break
            except Exception as e:
                console.print(f"[red]✗ {method_name} failed: {e}[/red]")
                continue
        
        if success and self.cookies:
            # Save to .env
            if self.save_to_env():
                console.print("\n[green]✓ Auth tokens saved to .env[/green]")
                
                # Test the tokens
                console.print("\n[cyan]Testing authentication...[/cyan]")
                if self.test_auth():
                    console.print("\n[bold green]🎉 OpenSea auth configured successfully![/bold green]")
                    console.print("\nYou can now run:")
                    console.print("  [cyan]mint_fcfs --chain base --contract 0x... --prewarm[/cyan]")
                else:
                    console.print("\n[yellow]⚠️  Tokens saved but may need verification[/yellow]")
            else:
                console.print("\n[red]✗ Failed to save to .env[/red]")
        else:
            console.print("\n[red]✗ Could not fetch auth tokens[/red]")
            console.print("\n[yellow]Please try manual method:[/yellow]")
            console.print("1. Open https://opensea.io")
            console.print("2. Login and copy cookies from DevTools")
            console.print("3. Paste into .env file")


def main():
    """Entry point"""
    auth = OpenSeaAutoAuth()
    auth.run()


if __name__ == "__main__":
    main()

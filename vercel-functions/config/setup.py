#!/usr/bin/env python3
# setup.py - Interactive setup script for Email AI Agent

import os
import sys
import json
from typing import Dict, Any
from getpass import getpass

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))
from client import EmailAgentConfig

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print setup header"""
    print("=" * 60)
    print("📧 EMAIL AI AGENT - INTERACTIVE SETUP")
    print("=" * 60)
    print("This script will help you configure your Email AI Agent")
    print("Make sure your Vercel deployment is complete before continuing.")
    print()

def get_basic_config() -> Dict[str, str]:
    """Get basic configuration (URL and API key)"""
    print("🔧 BASIC CONFIGURATION")
    print("-" * 30)
    
    # Get Vercel app URL
    while True:
        base_url = input("Enter your Vercel app URL (e.g., https://your-app.vercel.app): ").strip()
        if base_url.startswith('http'):
            break
        print("❌ URL must start with http:// or https://")
    
    # Get API secret key
    api_key = getpass("Enter your API secret key (hidden): ").strip()
    
    if not api_key:
        print("❌ API key is required")
        return get_basic_config()
    
    return {
        'base_url': base_url,
        'api_key': api_key
    }

def test_connection(config: EmailAgentConfig) -> bool:
    """Test basic connection to the API"""
    print("\n🔍 Testing connection to your API...")
    
    try:
        result = config.get_system_status()
        if result.get('success'):
            print("✅ Connection successful!")
            return True
        else:
            print(f"❌ Connection failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def setup_email_account(config: EmailAgentConfig) -> bool:
    """Interactive email account setup"""
    print("\n📧 EMAIL ACCOUNT SETUP")
    print("-" * 30)
    print("Choose your email provider:")
    print("1. Gmail (requires App Password)")
    print("2. Outlook/Microsoft 365")
    print("3. Yahoo (requires App Password)")
    print("4. Custom IMAP server")
    
    while True:
        choice = input("\nEnter choice (1-4): ").strip()
        if choice in ['1', '2', '3', '4']:
            break
        print("❌ Please enter 1, 2, 3, or 4")
    
    email = input("Enter your email address: ").strip()
    
    if choice == '1':  # Gmail
        print("\n📋 GMAIL SETUP INSTRUCTIONS:")
        print("1. Enable 2-Factor Authentication on your Google account")
        print("2. Go to Google Account → Security → App passwords")
        print("3. Generate password for 'Mail'")
        print("4. Use that password below (NOT your regular password)")
        print()
        
        app_password = getpass("Enter Gmail App Password (hidden): ").strip()
        result = config.add_gmail_account(email, app_password)
        
    elif choice == '2':  # Outlook
        password = getpass("Enter your Outlook password (hidden): ").strip()
        result = config.add_outlook_account(email, password)
        
    elif choice == '3':  # Yahoo
        print("\n📋 YAHOO SETUP INSTRUCTIONS:")
        print("1. Go to Yahoo Account Security settings")
        print("2. Generate App Password for 'Mail'")
        print("3. Use that password below")
        print()
        
        app_password = getpass("Enter Yahoo App Password (hidden): ").strip()
        result = config.add_yahoo_account(email, app_password)
        
    elif choice == '4':  # Custom IMAP
        print("\n📋 CUSTOM IMAP SETUP:")
        username = input("Enter username (often same as email): ").strip()
        password = getpass("Enter password (hidden): ").strip()
        imap_host = input("Enter IMAP server (e.g., mail.company.com): ").strip()
        
        imap_port = input("Enter IMAP port (default 993): ").strip()
        imap_port = int(imap_port) if imap_port else 993
        
        result = config.add_custom_imap_account(email, username, password, imap_host, imap_port)
    
    if result.get('success'):
        print(f"✅ Email account configured successfully!")
        return True
    else:
        print(f"❌ Email setup failed: {result.get('error')}")
        if result.get('details'):
            for detail in result['details']:
                print(f"   - {detail}")
        
        retry = input("\nWould you like to try again? (y/n): ").lower().startswith('y')
        if retry:
            return setup_email_account(config)
        return False

def setup_telegram(config: EmailAgentConfig) -> bool:
    """Interactive Telegram setup"""
    print("\n📱 TELEGRAM SETUP")
    print("-" * 30)
    
    # Show instructions
    instructions = input("Would you like to see Telegram setup instructions? (y/n): ").lower().startswith('y')
    if instructions:
        config.get_telegram_setup_instructions()
        input("\nPress Enter to continue...")
    
    print("\nEnter your Telegram configuration:")
    bot_token = input("Bot Token (from @BotFather): ").strip()
    chat_id = input("Your Chat ID: ").strip()
    username = input("Your Telegram username (optional): ").strip() or None
    
    result = config.set_telegram_config(bot_token, chat_id, username)
    
    if result.get('success'):
        print("✅ Telegram configured successfully!")
        print("📱 Check your Telegram for the test message")
        return True
    else:
        print(f"❌ Telegram setup failed: {result.get('error')}")
        
        retry = input("\nWould you like to try again? (y/n): ").lower().startswith('y')
        if retry:
            return setup_telegram(config)
        return False

def setup_ai(config: EmailAgentConfig) -> bool:
    """Interactive AI setup"""
    print("\n🤖 AI CONFIGURATION")
    print("-" * 30)
    
    # Show available providers
    providers_result = config.get_ai_providers()
    
    print("Choose your AI provider:")
    print("1. OpenAI (GPT-3.5/4) - Most popular, good quality")
    print("2. Anthropic (Claude) - Fast and efficient")
    
    while True:
        choice = input("\nEnter choice (1-2): ").strip()
        if choice in ['1', '2']:
            break
        print("❌ Please enter 1 or 2")
    
    if choice == '1':  # OpenAI
        print("\n📋 OPENAI SETUP:")
        print("1. Go to https://platform.openai.com/api-keys")
        print("2. Create a new API key")
        print("3. Make sure you have credits/billing set up")
        print()
        
        api_key = getpass("Enter OpenAI API key (sk-...): ").strip()
        
        print("\nChoose model:")
        print("1. gpt-3.5-turbo (cheaper, faster)")
        print("2. gpt-4 (better quality, more expensive)")
        print("3. gpt-4-turbo-preview (latest)")
        
        model_choice = input("Model choice (1-3, default 1): ").strip() or '1'
        model_map = {
            '1': 'gpt-3.5-turbo',
            '2': 'gpt-4', 
            '3': 'gpt-4-turbo-preview'
        }
        model = model_map.get(model_choice, 'gpt-3.5-turbo')
        
        result = config.set_openai_config(api_key, model)
        
    elif choice == '2':  # Anthropic
        print("\n📋 ANTHROPIC SETUP:")
        print("1. Go to https://console.anthropic.com/")
        print("2. Create a new API key")
        print("3. Make sure you have credits set up")
        print()
        
        api_key = getpass("Enter Anthropic API key (sk-ant-...): ").strip()
        
        print("\nChoose model:")
        print("1. claude-3-haiku (fastest, cheapest)")
        print("2. claude-3-sonnet (balanced)")
        print("3. claude-3-opus (highest quality)")
        
        model_choice = input("Model choice (1-3, default 1): ").strip() or '1'
        model_map = {
            '1': 'claude-3-haiku-20240307',
            '2': 'claude-3-sonnet-20240229',
            '3': 'claude-3-opus-20240229'
        }
        model = model_map.get(model_choice, 'claude-3-haiku-20240307')
        
        result = config.set_anthropic_config(api_key, model)
    
    if result.get('success'):
        print("✅ AI configuration successful!")
        return True
    else:
        print(f"❌ AI setup failed: {result.get('error')}")
        
        retry = input("\nWould you like to try again? (y/n): ").lower().startswith('y')
        if retry:
            return setup_ai(config)
        return False

def final_test(config: EmailAgentConfig) -> bool:
    """Run final system test"""
    print("\n🧪 FINAL SYSTEM TEST")
    print("-" * 30)
    print("Running complete system test...")
    
    # Trigger manual email check
    result = config.trigger_manual_check()
    
    if result.get('success'):
        processing_result = result.get('result', {})
        print(f"✅ System test passed!")
        print(f"   Accounts processed: {processing_result.get('accounts_processed', 0)}")
        print(f"   Emails processed: {processing_result.get('total_emails', 0)}")
        return True
    else:
        print(f"❌ System test failed: {result.get('error')}")
        return False

def show_next_steps():
    """Show what to do next"""
    print("\n🎉 SETUP COMPLETE!")
    print("=" * 30)
    print("Your Email AI Agent is now configured and running!")
    print()
    print("📋 What happens next:")
    print("   • The system will automatically check for emails every 5 minutes")
    print("   • New emails will be summarized using AI")
    print("   • Summaries will be sent to your Telegram")
    print()
    print("🔧 Useful commands:")
    print("   • Check status: python -c \"from config.client import *; c=EmailAgentConfig('URL','KEY'); c.get_system_status()\"")
    print("   • Manual check: python -c \"from config.client import *; c=EmailAgentConfig('URL','KEY'); c.trigger_manual_check()\"")
    print("   • View logs: python -c \"from config.client import *; c=EmailAgentConfig('URL','KEY'); c.get_system_logs()\"")
    print()
    print("📖 For more help, check the README.md file")

def save_config(basic_config: Dict[str, str]):
    """Save configuration for future use"""
    config_file = {
        'base_url': basic_config['base_url'],
        'setup_completed': True,
        'setup_date': str(datetime.now())
    }
    
    try:
        with open('.agent_config.json', 'w') as f:
            json.dump(config_file, f, indent=2)
        print(f"\n💾 Configuration saved to .agent_config.json")
    except:
        pass  # Non-critical

def main():
    """Main setup flow"""
    try:
        clear_screen()
        print_header()
        
        # Step 1: Get basic configuration
        basic_config = get_basic_config()
        config = EmailAgentConfig(basic_config['base_url'], basic_config['api_key'])
        
        # Step 2: Test connection
        if not test_connection(config):
            print("\n❌ Cannot connect to your API. Please check:")
            print("   1. Your Vercel app is deployed and running")
            print("   2. Environment variables are set correctly")
            print("   3. API_SECRET_KEY matches what you entered")
            return False
        
        print("\n" + "="*60)
        input("Press Enter to continue with configuration...")
        
        # Step 3: Email setup
        if not setup_email_account(config):
            print("\n❌ Email setup failed. Cannot continue.")
            return False
        
        # Step 4: Telegram setup
        if not setup_telegram(config):
            print("\n❌ Telegram setup failed. Cannot continue.")
            return False
        
        # Step 5: AI setup
        if not setup_ai(config):
            print("\n❌ AI setup failed. Cannot continue.")
            return False
        
        # Step 6: Final test
        print("\n" + "="*60)
        if not final_test(config):
            print("\n⚠️ Setup completed but final test failed.")
            print("Your configuration is saved, but you may need to debug issues.")
        
        # Step 7: Show next steps
        show_next_steps()
        save_config(basic_config)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user.")
        return False
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("Check your configuration and try again.")
        return False

if __name__ == "__main__":
    import datetime
    success = main()
    
    if success:
        print(f"\n✨ Setup completed successfully at {datetime.datetime.now()}")
        print("Your Email AI Agent is ready to use! 🚀")
    else:
        print(f"\n💔 Setup failed. Please check the errors above and try again.")
        
    input("\nPress Enter to exit...")
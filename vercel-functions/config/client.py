# config/client.py - Python Configuration Client
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class EmailAgentConfig:
    """Easy-to-use Python client for configuring Email AI Agent"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize configuration client
        
        Args:
            base_url: Your Vercel app URL (e.g., 'https://your-app.vercel.app')
            api_key: Your API secret key
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    # Email Account Management
    def add_gmail_account(self, email: str, app_password: str) -> Dict[str, Any]:
        """
        Add Gmail account (requires App Password)
        
        Steps to get App Password:
        1. Enable 2-Factor Authentication on your Google account
        2. Go to Google Account → Security → App passwords
        3. Generate password for 'Mail'
        4. Use that password here (not your regular password)
        """
        return self.add_email_account({
            'email': email,
            'provider': 'gmail',
            'username': email,
            'password': app_password
        })
    
    def add_outlook_account(self, email: str, password: str) -> Dict[str, Any]:
        """Add Outlook/Microsoft 365 account"""
        return self.add_email_account({
            'email': email,
            'provider': 'outlook', 
            'username': email,
            'password': password
        })
    
    def add_yahoo_account(self, email: str, app_password: str) -> Dict[str, Any]:
        """Add Yahoo account (requires App Password)"""
        return self.add_email_account({
            'email': email,
            'provider': 'yahoo',
            'username': email,
            'password': app_password
        })
    
    def add_custom_imap_account(self, email: str, username: str, password: str, 
                               imap_host: str, imap_port: int = 993) -> Dict[str, Any]:
        """Add custom IMAP account"""
        return self.add_email_account({
            'email': email,
            'provider': 'custom',
            'username': username,
            'password': password,
            'imap_host': imap_host,
            'imap_port': imap_port
        })
    
    def add_email_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add email account with validation and testing"""
        try:
            print(f"Adding email account: {account_data.get('email')}")
            
            response = requests.post(
                f"{self.base_url}/api/config-manager/email-account",
                headers=self.headers,
                json=account_data,
                timeout=60
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✅ Email account added successfully: {account_data.get('email')}")
                if result.get('connection_test', {}).get('success'):
                    unread_count = result['connection_test'].get('unread_count', 0)
                    print(f"📧 Connection test passed. Found {unread_count} unread emails.")
                return result
            else:
                print(f"❌ Failed to add email account: {result.get('error')}")
                if result.get('details'):
                    for detail in result['details']:
                        print(f"   - {detail}")
                return result
                
        except requests.exceptions.Timeout:
            error_result = {'success': False, 'error': 'Request timeout - server took too long to respond'}
            print(f"❌ {error_result['error']}")
            return error_result
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error adding email account: {e}")
            return error_result
    
    def test_email_account(self, account_id: str) -> Dict[str, Any]:
        """Test specific email account connection"""
        try:
            print(f"Testing email account: {account_id}")
            
            response = requests.post(
                f"{self.base_url}/api/config-manager/test-email",
                headers=self.headers,
                json={'account_id': account_id},
                timeout=30
            )
            
            result = response.json()
            
            if result.get('success'):
                print("✅ Email account test passed")
                if 'unread_count' in result:
                    print(f"📧 Found {result['unread_count']} unread emails")
            else:
                print(f"❌ Email account test failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error testing email account: {e}")
            return error_result
    
    def get_email_accounts(self) -> Dict[str, Any]:
        """Get all configured email accounts"""
        try:
            response = requests.get(
                f"{self.base_url}/api/config-manager/accounts",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success'):
                accounts = result.get('accounts', [])
                print(f"📋 Found {len(accounts)} email accounts:")
                for account in accounts:
                    status = "✅ Active" if account.get('is_active') else "❌ Inactive"
                    print(f"   - {account.get('email')} ({account.get('provider')}) {status}")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error getting email accounts: {e}")
            return error_result
    
    # Telegram Configuration
    def set_telegram_config(self, bot_token: str, chat_id: str, username: str = None) -> Dict[str, Any]:
        """
        Configure Telegram bot
        
        Steps to get bot token and chat ID:
        1. Message @BotFather on Telegram
        2. Send /newbot and follow instructions
        3. Save the bot token
        4. Message your bot, then visit: 
           https://api.telegram.org/bot<TOKEN>/getUpdates
        5. Find your chat ID in the response
        """
        try:
            config_data = {
                'bot_token': bot_token,
                'chat_id': chat_id
            }
            
            if username:
                config_data['username'] = username
            
            print("Setting up Telegram configuration...")
            
            response = requests.post(
                f"{self.base_url}/api/config-manager/telegram-config",
                headers=self.headers,
                json=config_data,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print("✅ Telegram configuration saved and tested successfully")
                print("📱 Test message should have been sent to your Telegram")
                return result
            else:
                print(f"❌ Telegram configuration failed: {result.get('error')}")
                if result.get('details'):
                    print(f"   Details: {result['details']}")
                return result
                
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error setting Telegram config: {e}")
            return error_result
    
    def test_telegram(self, custom_message: str = None) -> Dict[str, Any]:
        """Send test message to Telegram"""
        try:
            data = {}
            if custom_message:
                data['message'] = custom_message
            
            print("Sending Telegram test message...")
            
            response = requests.post(
                f"{self.base_url}/api/config-manager/test-telegram",
                headers=self.headers,
                json=data,
                timeout=15
            )
            
            result = response.json()
            
            if result.get('success'):
                print("✅ Telegram test message sent successfully")
            else:
                print(f"❌ Telegram test failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error testing Telegram: {e}")
            return error_result
    
    def get_telegram_setup_instructions(self) -> Dict[str, Any]:
        """Get detailed Telegram setup instructions"""
        try:
            response = requests.get(
                f"{self.base_url}/api/config-manager/telegram-setup",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success'):
                print(result.get('instructions', ''))
                
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error getting Telegram instructions: {e}")
            return error_result
    
    # AI Configuration
    def set_openai_config(self, api_key: str, model: str = 'gpt-3.5-turbo', 
                         max_tokens: int = 150, temperature: float = 0.3,
                         custom_prompt: str = None) -> Dict[str, Any]:
        """Configure OpenAI"""
        config_data = {
            'provider': 'openai',
            'api_key': api_key,
            'model': model,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        if custom_prompt:
            config_data['prompt_template'] = custom_prompt
        
        return self.set_ai_config(config_data)
    
    def set_anthropic_config(self, api_key: str, model: str = 'claude-3-haiku-20240307', 
                            max_tokens: int = 150, temperature: float = 0.3,
                            custom_prompt: str = None) -> Dict[str, Any]:
        """Configure Anthropic Claude"""
        config_data = {
            'provider': 'anthropic',
            'api_key': api_key,
            'model': model,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        if custom_prompt:
            config_data['prompt_template'] = custom_prompt
        
        return self.set_ai_config(config_data)
    
    def set_ai_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set AI configuration with validation"""
        try:
            provider = config_data.get('provider', 'unknown')
            print(f"Configuring AI provider: {provider}")
            
            response = requests.post(
                f"{self.base_url}/api/config-manager/ai-config",
                headers=self.headers,
                json=config_data,
                timeout=30
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get('success'):
                print(f"✅ AI configuration saved successfully: {provider}")
                model = config_data.get('model', 'unknown')
                print(f"🤖 Using model: {model}")
                
                # Show test result if available
                test_result = result.get('test_result', {})
                if test_result.get('api_connection', {}).get('success'):
                    print("✅ AI API connection test passed")
                
                return result
            else:
                print(f"❌ AI configuration failed: {result.get('error')}")
                if result.get('details'):
                    for detail in result['details']:
                        print(f"   - {detail}")
                return result
                
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error setting AI config: {e}")
            return error_result
    
    def get_ai_providers(self) -> Dict[str, Any]:
        """Get available AI providers and current configuration"""
        try:
            response = requests.get(
                f"{self.base_url}/api/config-manager/ai-providers",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success'):
                providers = result.get('providers', {})
                current = result.get('current_config', {})
                
                print("🤖 Available AI Providers:")
                for provider, info in providers.items():
                    print(f"   - {provider}: {info.get('notes', '')}")
                    print(f"     Default model: {info.get('default_model')}")
                    print(f"     Cost per 1k tokens: ~${info.get('cost_per_1k_tokens', 0)}")
                
                if current.get('configured'):
                    print(f"\n✅ Currently configured: {current.get('provider')} ({current.get('model')})")
                else:
                    print("\n❌ No AI provider configured")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error getting AI providers: {e}")
            return error_result
    
    # System Status and Monitoring
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            response = requests.get(
                f"{self.base_url}/api/config-manager/status",
                headers=self.headers,
                timeout=15
            )
            
            result = response.json()
            
            if result.get('success'):
                health = result.get('system_health', {})
                configs = result.get('configurations', {})
                
                print("📊 System Status:")
                print(f"   Active email accounts: {health.get('active_accounts', 0)}")
                print(f"   Emails processed (24h): {health.get('emails_last_24h', 0)}")
                print(f"   Database connected: {'✅' if health.get('database_connected') else '❌'}")
                
                telegram_ok = configs.get('telegram', {}).get('configured')
                ai_ok = configs.get('ai', {}).get('configured')
                
                print(f"   Telegram configured: {'✅' if telegram_ok else '❌'}")
                print(f"   AI configured: {'✅' if ai_ok else '❌'}")
                
                if health.get('last_activity'):
                    print(f"   Last activity: {health.get('last_activity')}")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error getting system status: {e}")
            return error_result
    
    def get_recent_emails(self, limit: int = 10) -> Dict[str, Any]:
        """Get recently processed emails"""
        try:
            response = requests.get(
                f"{self.base_url}/api/config-manager/recent-emails?limit={limit}",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('success'):
                emails = result.get('emails', [])
                print(f"📧 Recent {len(emails)} processed emails:")
                
                for email in emails[:5]:  # Show first 5
                    subject = email.get('subject', 'No subject')
                    sender = email.get('sender', 'Unknown')
                    sent = '✅' if email.get('telegram_sent') else '❌'
                    
                    # Truncate long subjects
                    if len(subject) > 50:
                        subject = subject[:47] + '...'
                    
                    print(f"   {sent} {subject}")
                    print(f"      From: {sender}")
                
                if len(emails) > 5:
                    print(f"   ... and {len(emails) - 5} more")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error getting recent emails: {e}")
            return error_result
    
    def trigger_manual_check(self) -> Dict[str, Any]:
        """Manually trigger email processing"""
        try:
            print("🔄 Triggering manual email check...")
            
            response = requests.post(
                f"{self.base_url}/api/email-processor",
                headers=self.headers,
                json={'trigger_type': 'manual'},
                timeout=120  # Email processing can take time
            )
            
            result = response.json()
            
            if result.get('success'):
                processing_result = result.get('result', {})
                accounts = processing_result.get('accounts_processed', 0)
                emails = processing_result.get('total_emails', 0)
                
                print(f"✅ Manual check completed")
                print(f"   Accounts processed: {accounts}")
                print(f"   Emails processed: {emails}")
                
                if processing_result.get('errors'):
                    print("⚠️ Some errors occurred:")
                    for error in processing_result['errors'][:3]:  # Show first 3
                        print(f"   - {error}")
                
            else:
                print(f"❌ Manual check failed: {result.get('error')}")
            
            return result
            
        except requests.exceptions.Timeout:
            error_result = {'success': False, 'error': 'Email processing timed out (this is normal for first run)'}
            print(f"⏰ {error_result['error']}")
            return error_result
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error triggering manual check: {e}")
            return error_result
    
    def get_system_logs(self, limit: int = 20, severity: str = None) -> Dict[str, Any]:
        """Get system logs for debugging"""
        try:
            url = f"{self.base_url}/api/config-manager/logs?limit={limit}"
            if severity:
                url += f"&severity={severity}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            result = response.json()
            
            if result.get('success'):
                logs = result.get('logs', [])
                print(f"📋 Recent {len(logs)} system logs:")
                
                for log in logs[:10]:  # Show first 10
                    timestamp = log.get('created_at', '')[:19]  # YYYY-MM-DD HH:MM:SS
                    event = log.get('event_type', 'unknown')
                    message = log.get('message', '')
                    severity = log.get('severity', 'info')
                    
                    # Severity emoji
                    emoji = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(severity, 'ℹ️')
                    
                    print(f"   {emoji} [{timestamp}] {event}: {message}")
                
                if len(logs) > 10:
                    print(f"   ... and {len(logs) - 10} more logs")
            
            return result
            
        except Exception as e:
            error_result = {'success': False, 'error': str(e)}
            print(f"❌ Error getting system logs: {e}")
            return error_result
    
    # Utility Methods
    def setup_complete_system(self, email_config: Dict[str, Any], 
                             telegram_config: Dict[str, Any], 
                             ai_config: Dict[str, Any]) -> Dict[str, Any]:
        """Set up complete system in one go"""
        print("🚀 Setting up complete Email AI Agent system...\n")
        
        results = {
            'email': None,
            'telegram': None,
            'ai': None,
            'test': None
        }
        
        # Step 1: Add email account
        print("Step 1: Configuring email account...")
        results['email'] = self.add_email_account(email_config)
        
        if not results['email'].get('success'):
            print("❌ Email configuration failed. Stopping setup.")
            return {'success': False, 'results': results}
        
        print()
        
        # Step 2: Set up Telegram
        print("Step 2: Configuring Telegram...")
        results['telegram'] = self.set_telegram_config(**telegram_config)
        
        if not results['telegram'].get('success'):
            print("❌ Telegram configuration failed. Stopping setup.")
            return {'success': False, 'results': results}
        
        print()
        
        # Step 3: Set up AI
        print("Step 3: Configuring AI...")
        results['ai'] = self.set_ai_config(ai_config)
        
        if not results['ai'].get('success'):
            print("❌ AI configuration failed. Stopping setup.")
            return {'success': False, 'results': results}
        
        print()
        
        # Step 4: Test the complete system
        print("Step 4: Testing complete system...")
        results['test'] = self.trigger_manual_check()
        
        print()
        
        if all(r.get('success') for r in results.values() if r):
            print("🎉 Email AI Agent setup completed successfully!")
            print("\n📋 Next steps:")
            print("   1. The system will automatically check emails every 5 minutes")
            print("   2. Check system status with: config.get_system_status()")
            print("   3. View recent emails with: config.get_recent_emails()")
            print("   4. Monitor logs with: config.get_system_logs()")
            
            return {'success': True, 'results': results}
        else:
            print("⚠️ Setup completed with some issues. Check individual results.")
            return {'success': False, 'results': results}
    
    def health_check(self) -> bool:
        """Quick health check - returns True if system is operational"""
        try:
            status = self.get_system_status()
            
            if not status.get('success'):
                return False
            
            health = status.get('system_health', {})
            configs = status.get('configurations', {})
            
            # Check critical components
            database_ok = health.get('database_connected', False)
            telegram_ok = configs.get('telegram', {}).get('configured', False)
            ai_ok = configs.get('ai', {}).get('configured', False)
            has_accounts = health.get('active_accounts', 0) > 0
            
            return database_ok and telegram_ok and ai_ok and has_accounts
            
        except:
            return False


# Example usage and testing
def example_usage():
    """Example of how to use the configuration client"""
    
    # Initialize client
    config = EmailAgentConfig(
        base_url='https://your-app.vercel.app',
        api_key='your-secret-key'
    )
    
    # Example 1: Add Gmail account
    gmail_result = config.add_gmail_account(
        email='your-email@gmail.com',
        app_password='your-app-password'  # Not your regular password!
    )
    
    # Example 2: Set up Telegram
    telegram_result = config.set_telegram_config(
        bot_token='123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
        chat_id='your-chat-id'
    )
    
    # Example 3: Configure OpenAI
    ai_result = config.set_openai_config(
        api_key='sk-your-openai-key',
        model='gpt-3.5-turbo'
    )
    
    # Example 4: Test the system
    if all([gmail_result.get('success'), telegram_result.get('success'), ai_result.get('success')]):
        print("\n🧪 Testing complete system...")
        test_result = config.trigger_manual_check()
        
        if test_result.get('success'):
            print("✅ System is working correctly!")
        else:
            print("❌ System test failed")
    
    # Example 5: Monitor system
    config.get_system_status()
    config.get_recent_emails(5)


if __name__ == "__main__":
    print("Email AI Agent Configuration Client")
    print("=" * 40)
    example_usage()
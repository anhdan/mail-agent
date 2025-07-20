# utils/database.py - Supabase Database Utilities
import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from supabase import create_client, Client
from cryptography.fernet import Fernet
import base64

class DatabaseManager:
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for passwords"""
        key = os.environ.get('ENCRYPTION_KEY')
        if key:
            return base64.urlsafe_b64decode(key.encode())
        else:
            # Generate new key (in production, store this securely)
            return Fernet.generate_key()
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt password for storage"""
        return self.cipher.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password for use"""
        try:
            return self.cipher.decrypt(encrypted_password.encode()).decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            # Fallback for base64 encoded passwords (during migration)
            try:
                return base64.b64decode(encrypted_password).decode()
            except:
                return encrypted_password  # Return as-is if not encrypted
    
    # Email Accounts Management
    def get_active_email_accounts(self) -> List[Dict[str, Any]]:
        """Get all active email accounts"""
        try:
            response = self.client.table('email_accounts')\
                .select('*')\
                .eq('is_active', True)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching email accounts: {e}")
            return []
    
    def add_email_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new email account"""
        try:
            # Encrypt password
            if 'password' in account_data:
                account_data['encrypted_password'] = self.encrypt_password(account_data['password'])
                del account_data['password']  # Remove plain password
            
            response = self.client.table('email_accounts')\
                .insert(account_data)\
                .execute()
            
            if response.data:
                self.log_system_event('email_account_added', 
                                    f"Added email account: {account_data.get('email')}")
                return response.data[0]
            else:
                raise Exception("Failed to insert email account")
                
        except Exception as e:
            print(f"Error adding email account: {e}")
            raise e
    
    def update_account_last_check(self, account_id: str, timestamp: Optional[datetime] = None):
        """Update last check time for account"""
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            self.client.table('email_accounts')\
                .update({'last_check_time': timestamp.isoformat()})\
                .eq('id', account_id)\
                .execute()
        except Exception as e:
            print(f"Error updating last check time: {e}")
    
    # Processed Emails Management
    def is_email_processed(self, account_id: str, message_id: str) -> bool:
        """Check if email was already processed"""
        try:
            response = self.client.table('processed_emails')\
                .select('id')\
                .eq('account_id', account_id)\
                .eq('message_id', message_id)\
                .execute()
            
            return len(response.data) > 0 if response.data else False
        except Exception as e:
            print(f"Error checking processed email: {e}")
            return False
    
    def store_processed_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store processed email in database"""
        try:
            response = self.client.table('processed_emails')\
                .insert(email_data)\
                .execute()
            
            if response.data:
                return response.data[0]
            else:
                raise Exception("Failed to store processed email")
                
        except Exception as e:
            print(f"Error storing processed email: {e}")
            raise e
    
    def mark_telegram_sent(self, email_id: str, success: bool = True):
        """Mark email as sent to Telegram"""
        try:
            update_data = {
                'telegram_sent': success,
                'telegram_sent_at': datetime.now().isoformat() if success else None
            }
            
            self.client.table('processed_emails')\
                .update(update_data)\
                .eq('id', email_id)\
                .execute()
                
        except Exception as e:
            print(f"Error marking telegram sent: {e}")
    
    def get_recent_emails(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent processed emails"""
        try:
            response = self.client.table('processed_emails')\
                .select('''
                    id, subject, sender, received_date, summary, 
                    telegram_sent, created_at,
                    email_accounts!inner(email)
                ''')\
                .order('received_date', desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching recent emails: {e}")
            return []
    
    # Configuration Management
    def get_telegram_config(self) -> Optional[Dict[str, Any]]:
        """Get active Telegram configuration"""
        try:
            response = self.client.table('telegram_config')\
                .select('*')\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching Telegram config: {e}")
            return None
    
    def set_telegram_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set Telegram configuration"""
        try:
            # Deactivate existing configs
            self.client.table('telegram_config')\
                .update({'is_active': False})\
                .eq('is_active', True)\
                .execute()
            
            # Insert new config
            config_data['is_active'] = True
            response = self.client.table('telegram_config')\
                .insert(config_data)\
                .execute()
            
            if response.data:
                self.log_system_event('telegram_config_updated', 
                                    "Telegram configuration updated")
                return response.data[0]
            else:
                raise Exception("Failed to set Telegram config")
                
        except Exception as e:
            print(f"Error setting Telegram config: {e}")
            raise e
    
    def get_ai_config(self) -> Optional[Dict[str, Any]]:
        """Get active AI configuration"""
        try:
            response = self.client.table('ai_config')\
                .select('*')\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching AI config: {e}")
            return None
    
    def set_ai_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set AI configuration"""
        try:
            # Encrypt API key
            if 'api_key' in config_data:
                config_data['api_key_encrypted'] = self.encrypt_password(config_data['api_key'])
                del config_data['api_key']  # Remove plain API key
            
            # Deactivate existing configs
            self.client.table('ai_config')\
                .update({'is_active': False})\
                .eq('is_active', True)\
                .execute()
            
            # Insert new config
            config_data['is_active'] = True
            response = self.client.table('ai_config')\
                .insert(config_data)\
                .execute()
            
            if response.data:
                self.log_system_event('ai_config_updated', 
                                    f"AI configuration updated: {config_data.get('provider')}")
                return response.data[0]
            else:
                raise Exception("Failed to set AI config")
                
        except Exception as e:
            print(f"Error setting AI config: {e}")
            raise e
    
    # System Logging
    def log_system_event(self, event_type: str, message: str, 
                        account_id: Optional[str] = None, 
                        metadata: Optional[Dict] = None,
                        severity: str = 'info'):
        """Log system event"""
        try:
            log_data = {
                'event_type': event_type,
                'message': message,
                'severity': severity,
                'created_at': datetime.now().isoformat()
            }
            
            if account_id:
                log_data['account_id'] = account_id
            
            if metadata:
                log_data['metadata'] = json.dumps(metadata)
            
            self.client.table('system_logs')\
                .insert(log_data)\
                .execute()
                
        except Exception as e:
            print(f"Error logging system event: {e}")
    
    # System Health and Statistics
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            # Use the database function we created
            response = self.client.rpc('get_system_health').execute()
            
            if response.data:
                return response.data
            else:
                # Fallback manual calculation
                return self._calculate_system_health_manual()
                
        except Exception as e:
            print(f"Error getting system health: {e}")
            return self._calculate_system_health_manual()
    
    def _calculate_system_health_manual(self) -> Dict[str, Any]:
        """Manual system health calculation (fallback)"""
        try:
            # Count active accounts
            accounts_response = self.client.table('email_accounts')\
                .select('id', count='exact')\
                .eq('is_active', True)\
                .execute()
            
            # Count recent emails
            emails_response = self.client.table('processed_emails')\
                .select('id', count='exact')\
                .gte('created_at', datetime.now().replace(hour=0, minute=0, second=0).isoformat())\
                .execute()
            
            # Check configurations
            telegram_config = self.get_telegram_config()
            ai_config = self.get_ai_config()
            
            return {
                'active_accounts': accounts_response.count or 0,
                'emails_last_24h': emails_response.count or 0,
                'telegram_configured': telegram_config is not None,
                'ai_configured': ai_config is not None,
                'database_connected': True,
                'check_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error in manual health calculation: {e}")
            return {
                'database_connected': False,
                'error': str(e),
                'check_timestamp': datetime.now().isoformat()
            }
    
    def get_email_stats(self) -> List[Dict[str, Any]]:
        """Get email statistics using the view"""
        try:
            response = self.client.table('email_stats')\
                .select('*')\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching email stats: {e}")
            return []
    
    def cleanup_old_emails(self) -> int:
        """Run cleanup of old emails"""
        try:
            response = self.client.rpc('cleanup_old_emails').execute()
            
            if response.data:
                deleted_count = response.data
                self.log_system_event('cleanup_completed', 
                                    f"Cleaned up {deleted_count} old emails")
                return deleted_count
            else:
                return 0
                
        except Exception as e:
            print(f"Error cleaning up old emails: {e}")
            self.log_system_event('cleanup_failed', 
                                f"Failed to cleanup old emails: {str(e)}", 
                                severity='error')
            return 0

# Create global database instance
db = DatabaseManager()
# api/config-manager.py - Configuration Management API
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import traceback

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database import db
from utils.email_utils import get_provider_settings, validate_email_account, EmailProcessor
from utils.ai_utils import validate_ai_config, get_ai_provider_info, AIProcessor
from utils.telegram_utils import validate_telegram_config, TelegramNotifier, get_telegram_setup_instructions

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests for configuration"""
        try:
            # Parse URL to get endpoint
            parsed_url = urlparse(self.path)
            path_parts = [p for p in parsed_url.path.split('/') if p]
            
            # Remove 'api' and 'config-manager' from path
            if len(path_parts) >= 2 and path_parts[0] == 'api' and path_parts[1] == 'config-manager':
                endpoint = path_parts[2] if len(path_parts) > 2 else ''
            else:
                endpoint = path_parts[-1] if path_parts else ''
            
            # Verify authorization
            if not self._verify_authorization():
                self._send_error(401, 'Unauthorized')
                return
            
            # Get request data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
            else:
                request_data = {}
            
            print(f"POST to endpoint: {endpoint}")
            
            # Route to appropriate handler
            if endpoint == 'email-account':
                result = self._add_email_account(request_data)
            elif endpoint == 'telegram-config':
                result = self._set_telegram_config(request_data)
            elif endpoint == 'ai-config':
                result = self._set_ai_config(request_data)
            elif endpoint == 'test-telegram':
                result = self._test_telegram(request_data)
            elif endpoint == 'test-email':
                result = self._test_email_account(request_data)
            else:
                self._send_error(404, f'Endpoint not found: {endpoint}')
                return
            
            self._send_json_response(result)
            
        except json.JSONDecodeError:
            self._send_error(400, 'Invalid JSON in request body')
        except Exception as e:
            error_msg = f"Configuration error: {str(e)}"
            print(f"ERROR: {error_msg}")
            print(traceback.format_exc())
            self._send_error(500, error_msg)
    
    def do_GET(self):
        """Handle GET requests for retrieving configuration"""
        try:
            # Parse URL
            parsed_url = urlparse(self.path)
            path_parts = [p for p in parsed_url.path.split('/') if p]
            query_params = parse_qs(parsed_url.query)
            
            # Remove 'api' and 'config-manager' from path
            if len(path_parts) >= 2 and path_parts[0] == 'api' and path_parts[1] == 'config-manager':
                endpoint = path_parts[2] if len(path_parts) > 2 else ''
            else:
                endpoint = path_parts[-1] if path_parts else ''
            
            # Verify authorization
            if not self._verify_authorization():
                self._send_error(401, 'Unauthorized')
                return
            
            print(f"GET to endpoint: {endpoint}")
            
            # Route to appropriate handler
            if endpoint == 'status' or endpoint == '':
                result = self._get_system_status()
            elif endpoint == 'accounts':
                result = self._get_email_accounts()
            elif endpoint == 'recent-emails':
                limit = int(query_params.get('limit', [20])[0])
                result = self._get_recent_emails(limit)
            elif endpoint == 'telegram-setup':
                result = self._get_telegram_setup()
            elif endpoint == 'ai-providers':
                result = self._get_ai_providers()
            elif endpoint == 'email-providers':
                result = self._get_email_providers()
            elif endpoint == 'logs':
                limit = int(query_params.get('limit', [50])[0])
                severity = query_params.get('severity', [None])[0]
                result = self._get_system_logs(limit, severity)
            else:
                self._send_error(404, f'Endpoint not found: {endpoint}')
                return
            
            self._send_json_response(result)
            
        except Exception as e:
            error_msg = f"Configuration retrieval error: {str(e)}"
            print(f"ERROR: {error_msg}")
            self._send_error(500, error_msg)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
    
    def _verify_authorization(self) -> bool:
        """Verify request authorization"""
        auth_header = self.headers.get('Authorization')
        expected_key = os.environ.get('API_SECRET_KEY')
        
        if not expected_key:
            print("WARNING: API_SECRET_KEY not set, skipping authorization")
            return True
        
        if not auth_header:
            return False
        
        return auth_header == f"Bearer {expected_key}"
    
    # Email Account Management
    def _add_email_account(self, data: dict) -> dict:
        """Add new email account"""
        try:
            # Validate input data
            validation = validate_email_account(data)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'details': validation['errors']
                }
            
            account_data = validation['account_data']
            
            # Get provider settings
            provider_settings = get_provider_settings(
                account_data['provider'],
                account_data.get('imap_host'),
                account_data.get('imap_port')
            )
            
            # Merge provider settings
            account_data.update(provider_settings)
            
            # Test email connection before saving
            test_result = self._test_email_connection(account_data)
            if not test_result['success']:
                return {
                    'success': False,
                    'error': 'Email connection test failed',
                    'details': test_result['error']
                }
            
            # Add to database
            stored_account = db.add_email_account(account_data)
            
            # Remove sensitive data from response
            safe_account = {k: v for k, v in stored_account.items() 
                          if k not in ['encrypted_password', 'oauth_refresh_token']}
            
            return {
                'success': True,
                'message': f'Email account added successfully: {account_data["email"]}',
                'account': safe_account,
                'connection_test': test_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to add email account: {str(e)}'
            }
    
    def _test_email_connection(self, account_data: dict) -> dict:
        """Test email account connection"""
        processor = EmailProcessor()
        try:
            success = processor.connect_to_imap(account_data, account_data['password'])
            
            if success:
                # Try to get email count
                emails = processor.get_unread_emails()
                processor.close_connection()
                
                return {
                    'success': True,
                    'message': f'Successfully connected to {account_data["email"]}',
                    'unread_count': len(emails)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to connect to IMAP server'
                }
                
        except Exception as e:
            processor.close_connection()
            return {
                'success': False,
                'error': f'Connection test failed: {str(e)}'
            }
    
    def _get_email_accounts(self) -> dict:
        """Get all email accounts"""
        try:
            accounts = db.get_active_email_accounts()
            
            # Remove sensitive data
            safe_accounts = []
            for account in accounts:
                safe_account = {k: v for k, v in account.items() 
                              if k not in ['encrypted_password', 'oauth_refresh_token']}
                safe_accounts.append(safe_account)
            
            return {
                'success': True,
                'accounts': safe_accounts,
                'count': len(safe_accounts)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to retrieve email accounts: {str(e)}'
            }
    
    def _test_email_account(self, data: dict) -> dict:
        """Test specific email account"""
        try:
            account_id = data.get('account_id')
            if not account_id:
                return {
                    'success': False,
                    'error': 'Account ID is required'
                }
            
            # Get account from database
            accounts = db.get_active_email_accounts()
            account = next((acc for acc in accounts if acc['id'] == account_id), None)
            
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            # Test connection
            password = db.decrypt_password(account['encrypted_password'])
            test_result = self._test_email_connection({**account, 'password': password})
            
            return test_result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to test email account: {str(e)}'
            }
    
    # Telegram Configuration
    def _set_telegram_config(self, data: dict) -> dict:
        """Set Telegram configuration"""
        try:
            # Validate input
            validation = validate_telegram_config(data)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': 'Telegram validation failed',
                    'details': validation['errors']
                }
            
            config_data = validation['config_data']
            
            # Test Telegram connection
            notifier = TelegramNotifier(config_data)
            test_result = notifier.send_test_message()
            
            if not test_result['success']:
                return {
                    'success': False,
                    'error': 'Telegram test failed',
                    'details': test_result['error']
                }
            
            # Save to database
            stored_config = db.set_telegram_config(config_data)
            
            # Remove sensitive data
            safe_config = {k: v for k, v in stored_config.items() 
                          if k not in ['bot_token']}
            
            return {
                'success': True,
                'message': 'Telegram configuration saved and tested successfully',
                'config': safe_config,
                'test_result': test_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to set Telegram config: {str(e)}'
            }
    
    def _test_telegram(self, data: dict) -> dict:
        """Test Telegram configuration"""
        try:
            config = db.get_telegram_config()
            if not config:
                return {
                    'success': False,
                    'error': 'No Telegram configuration found'
                }
            
            notifier = TelegramNotifier(config)
            custom_message = data.get('message')
            
            result = notifier.send_test_message(custom_message)
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Telegram test failed: {str(e)}'
            }
    
    def _get_telegram_setup(self) -> dict:
        """Get Telegram setup instructions"""
        return {
            'success': True,
            'instructions': get_telegram_setup_instructions(),
            'current_config': self._get_current_telegram_config()
        }
    
    def _get_current_telegram_config(self) -> dict:
        """Get current Telegram configuration (without sensitive data)"""
        try:
            config = db.get_telegram_config()
            if config:
                return {
                    'configured': True,
                    'chat_id': config.get('chat_id'),
                    'username': config.get('username'),
                    'is_active': config.get('is_active')
                }
            else:
                return {'configured': False}
        except:
            return {'configured': False, 'error': 'Failed to check configuration'}
    
    # AI Configuration
    def _set_ai_config(self, data: dict) -> dict:
        """Set AI configuration"""
        try:
            # Validate input
            validation = validate_ai_config(data)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': 'AI validation failed',
                    'details': validation['errors']
                }
            
            config_data = validation['config_data']
            
            # Test AI connection
            try:
                processor = AIProcessor(config_data, lambda x: x)  # Don't decrypt for test
                test_result = processor.validate_configuration()
                
                if not test_result['valid']:
                    return {
                        'success': False,
                        'error': 'AI configuration test failed',
                        'details': test_result['errors']
                    }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'AI test failed: {str(e)}'
                }
            
            # Save to database
            stored_config = db.set_ai_config(config_data)
            
            # Remove sensitive data
            safe_config = {k: v for k, v in stored_config.items() 
                          if k not in ['api_key_encrypted']}
            
            return {
                'success': True,
                'message': f'AI configuration saved successfully: {config_data["provider"]}',
                'config': safe_config,
                'test_result': test_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to set AI config: {str(e)}'
            }
    
    def _get_ai_providers(self) -> dict:
        """Get available AI providers"""
        from utils.ai_utils import AI_PROVIDERS
        
        return {
            'success': True,
            'providers': AI_PROVIDERS,
            'current_config': self._get_current_ai_config()
        }
    
    def _get_current_ai_config(self) -> dict:
        """Get current AI configuration (without sensitive data)"""
        try:
            config = db.get_ai_config()
            if config:
                return {
                    'configured': True,
                    'provider': config.get('provider'),
                    'model': config.get('model'),
                    'max_tokens': config.get('max_tokens'),
                    'temperature': config.get('temperature'),
                    'is_active': config.get('is_active')
                }
            else:
                return {'configured': False}
        except:
            return {'configured': False, 'error': 'Failed to check configuration'}
    
    # System Status and Information
    def _get_system_status(self) -> dict:
        """Get comprehensive system status"""
        try:
            # Get basic health
            health = db.get_system_health()
            
            # Get email stats
            email_stats = db.get_email_stats()
            
            # Get configuration status
            telegram_status = self._get_current_telegram_config()
            ai_status = self._get_current_ai_config()
            
            return {
                'success': True,
                'system_health': health,
                'email_stats': email_stats,
                'configurations': {
                    'telegram': telegram_status,
                    'ai': ai_status
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get system status: {str(e)}'
            }
    
    def _get_recent_emails(self, limit: int = 20) -> dict:
        """Get recent processed emails"""
        try:
            emails = db.get_recent_emails(limit)
            
            return {
                'success': True,
                'emails': emails,
                'count': len(emails)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get recent emails: {str(e)}'
            }
    
    def _get_email_providers(self) -> dict:
        """Get supported email providers"""
        from utils.email_utils import EMAIL_PROVIDERS
        
        return {
            'success': True,
            'providers': EMAIL_PROVIDERS
        }
    
    def _get_system_logs(self, limit: int = 50, severity: str = None) -> dict:
        """Get system logs"""
        try:
            # Build query
            query = db.client.table('system_logs').select('*')
            
            if severity:
                query = query.eq('severity', severity)
            
            query = query.order('created_at', desc=True).limit(limit)
            
            response = query.execute()
            
            return {
                'success': True,
                'logs': response.data if response.data else [],
                'count': len(response.data) if response.data else 0,
                'filters': {
                    'severity': severity,
                    'limit': limit
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get system logs: {str(e)}'
            }
    
    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2, default=str)
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error(self, status_code: int, message: str):
        """Send error response"""
        self._send_json_response({
            'success': False,
            'error': message,
            'timestamp': datetime.now().isoformat()
        }, status_code)

# For local testing
if __name__ == "__main__":
    print("Testing configuration manager locally...")
    
    # Mock request for testing
    class MockRequest:
        def __init__(self):
            self.headers = {'Authorization': 'Bearer test-key'}
            self.path = '/api/config-manager/status'
    
    os.environ.setdefault('API_SECRET_KEY', 'test-key')
    
    h = handler(MockRequest(), None, None)
    h.do_GET()
    
    print("Local test completed")
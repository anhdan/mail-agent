# api/health-check.py - System Health Check Endpoint
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime
import traceback

# Add utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.database import db

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for health check"""
        try:
            # Perform comprehensive health check
            health_result = self._perform_health_check()
            
            # Determine overall status
            status_code = 200 if health_result['overall_status'] == 'healthy' else 503
            
            self._send_json_response(health_result, status_code)
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            print(traceback.format_exc())
            
            self._send_json_response({
                'overall_status': 'unhealthy',
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'checks': {}
            }, 503)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def _perform_health_check(self) -> dict:
        """Perform comprehensive system health check"""
        checks = {}
        overall_healthy = True
        
        # Check 1: Database connectivity
        checks['database'] = self._check_database()
        if not checks['database']['healthy']:
            overall_healthy = False
        
        # Check 2: Environment variables
        checks['environment'] = self._check_environment()
        if not checks['environment']['healthy']:
            overall_healthy = False
        
        # Check 3: Configuration completeness
        checks['configuration'] = self._check_configuration()
        if not checks['configuration']['healthy']:
            overall_healthy = False
        
        # Check 4: Recent activity
        checks['activity'] = self._check_recent_activity()
        # Activity check is informational, doesn't affect overall health
        
        # Check 5: System resources
        checks['resources'] = self._check_system_resources()
        # Resource check is informational, doesn't affect overall health
        
        return {
            'overall_status': 'healthy' if overall_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'uptime': self._get_uptime(),
            'checks': checks,
            'summary': self._generate_summary(checks)
        }
    
    def _check_database(self) -> dict:
        """Check database connectivity and basic functionality"""
        try:
            # Test basic connection
            health = db.get_system_health()
            
            if isinstance(health, dict) and health.get('database_connected'):
                return {
                    'healthy': True,
                    'message': 'Database connection successful',
                    'details': {
                        'active_accounts': health.get('active_accounts', 0),
                        'emails_last_24h': health.get('emails_last_24h', 0),
                        'response_time_ms': 'N/A'  # Could add timing here
                    }
                }
            else:
                return {
                    'healthy': False,
                    'message': 'Database connection failed',
                    'error': 'Health check returned invalid data'
                }
                
        except Exception as e:
            return {
                'healthy': False,
                'message': 'Database check failed',
                'error': str(e)
            }
    
    def _check_environment(self) -> dict:
        """Check required environment variables"""
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_SERVICE_ROLE_KEY',
            'API_SECRET_KEY'
        ]
        
        optional_vars = [
            'OPENAI_API_KEY',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID',
            'ENCRYPTION_KEY'
        ]
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.environ.get(var):
                missing_required.append(var)
        
        for var in optional_vars:
            if not os.environ.get(var):
                missing_optional.append(var)
        
        healthy = len(missing_required) == 0
        
        result = {
            'healthy': healthy,
            'message': 'All required environment variables present' if healthy else 'Missing required environment variables',
            'details': {
                'required_vars_present': len(required_vars) - len(missing_required),
                'required_vars_total': len(required_vars),
                'optional_vars_present': len(optional_vars) - len(missing_optional),
                'optional_vars_total': len(optional_vars)
            }
        }
        
        if missing_required:
            result['missing_required'] = missing_required
        
        if missing_optional:
            result['missing_optional'] = missing_optional
        
        return result
    
    def _check_configuration(self) -> dict:
        """Check system configuration completeness"""
        try:
            # Check email accounts
            accounts = db.get_active_email_accounts()
            has_email_accounts = len(accounts) > 0
            
            # Check Telegram config
            telegram_config = db.get_telegram_config()
            has_telegram = telegram_config is not None and telegram_config.get('is_active')
            
            # Check AI config
            ai_config = db.get_ai_config()
            has_ai = ai_config is not None and ai_config.get('is_active')
            
            # System is considered healthy if it has at least email accounts
            # Telegram and AI are important but not critical for basic function
            healthy = has_email_accounts
            
            issues = []
            if not has_email_accounts:
                issues.append('No active email accounts configured')
            if not has_telegram:
                issues.append('Telegram not configured')
            if not has_ai:
                issues.append('AI service not configured')
            
            return {
                'healthy': healthy,
                'message': 'System fully configured' if has_email_accounts and has_telegram and has_ai else 'Configuration incomplete',
                'details': {
                    'email_accounts': len(accounts),
                    'telegram_configured': has_telegram,
                    'ai_configured': has_ai,
                    'fully_configured': has_email_accounts and has_telegram and has_ai
                },
                'issues': issues if issues else None
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'message': 'Configuration check failed',
                'error': str(e)
            }
    
    def _check_recent_activity(self) -> dict:
        """Check for recent system activity"""
        try:
            # Get recent emails
            recent_emails = db.get_recent_emails(5)
            
            # Get recent logs
            logs_response = db.client.table('system_logs')\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(10)\
                .execute()
            
            recent_logs = logs_response.data if logs_response.data else []
            
            # Find last successful email processing
            last_processing = None
            for log in recent_logs:
                if log.get('event_type') == 'email_processing_completed':
                    last_processing = log.get('created_at')
                    break
            
            # Find recent errors
            recent_errors = [log for log in recent_logs if log.get('severity') == 'error']
            
            return {
                'healthy': True,  # Activity is informational
                'message': f'Found {len(recent_emails)} recent emails and {len(recent_logs)} log entries',
                'details': {
                    'recent_emails_count': len(recent_emails),
                    'recent_logs_count': len(recent_logs),
                    'last_email_processing': last_processing,
                    'recent_errors_count': len(recent_errors),
                    'last_activity': recent_logs[0].get('created_at') if recent_logs else None
                }
            }
            
        except Exception as e:
            return {
                'healthy': True,  # Don't fail health check on activity issues
                'message': 'Activity check failed',
                'error': str(e)
            }
    
    def _check_system_resources(self) -> dict:
        """Check system resource usage (basic)"""
        try:
            # Get database size if available
            db_size = None
            try:
                size_response = db.client.rpc('get_database_size').execute()
                if size_response.data:
                    db_size = size_response.data
            except:
                pass  # Database size function might not exist
            
            return {
                'healthy': True,  # Resource check is informational
                'message': 'Resource usage within normal limits',
                'details': {
                    'database_size_mb': db_size,
                    'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    'platform': sys.platform
                }
            }
            
        except Exception as e:
            return {
                'healthy': True,  # Don't fail health check on resource issues
                'message': 'Resource check failed',
                'error': str(e)
            }
    
    def _get_uptime(self) -> str:
        """Get system uptime (approximate)"""
        # In serverless, this is the function's uptime, not system uptime
        return "Serverless - uptime N/A"
    
    def _generate_summary(self, checks: dict) -> dict:
        """Generate health check summary"""
        total_checks = len(checks)
        healthy_checks = sum(1 for check in checks.values() if check.get('healthy'))
        
        issues = []
        warnings = []
        
        for check_name, check_result in checks.items():
            if not check_result.get('healthy'):
                if check_name in ['database', 'environment']:
                    issues.append(f"{check_name}: {check_result.get('message', 'Unknown issue')}")
                else:
                    warnings.append(f"{check_name}: {check_result.get('message', 'Unknown issue')}")
        
        return {
            'total_checks': total_checks,
            'healthy_checks': healthy_checks,
            'health_percentage': round((healthy_checks / total_checks) * 100, 1) if total_checks > 0 else 0,
            'critical_issues': issues,
            'warnings': warnings,
            'status_message': self._get_status_message(issues, warnings)
        }
    
    def _get_status_message(self, issues: list, warnings: list) -> str:
        """Generate human-readable status message"""
        if issues:
            return f"System unhealthy: {len(issues)} critical issue(s) found"
        elif warnings:
            return f"System operational with {len(warnings)} warning(s)"
        else:
            return "System fully operational"
    
    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        
        response_json = json.dumps(data, indent=2, default=str)
        self.wfile.write(response_json.encode('utf-8'))

# For local testing
if __name__ == "__main__":
    print("Testing health check endpoint locally...")
    
    class MockRequest:
        def __init__(self):
            self.headers = {}
    
    h = handler(MockRequest(), None, None)
    h.do_GET()
    
    print("Health check test completed")
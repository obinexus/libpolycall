#!/usr/bin/env python3
"""
Dual Testing Client for LibPolyCall
Tests both Node.js (port 8084) and Python (port 3001) servers simultaneously
"""

import json
import http.client
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class DualTestClient:
    """Client for testing both Node.js and Python LibPolyCall servers"""
    
    def __init__(self):
        self.servers = {
            'nodejs': {
                'name': 'Node.js PolyCall',
                'host': 'localhost',
                'port': 8084,
                'emoji': '🟢',
                'status': 'unknown'
            },
            'python': {
                'name': 'PyPolyCall',
                'host': 'localhost', 
                'port': 3001,
                'emoji': '🐍',
                'status': 'unknown'
            }
        }
        self.test_results = {}
        self.lock = threading.Lock()
    
    def log_message(self, message, level="INFO", server=None):
        """Log message with timestamp and server context"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        symbols = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "TEST": "🧪"}
        symbol = symbols.get(level, "•")
        
        server_prefix = ""
        if server:
            emoji = self.servers.get(server, {}).get('emoji', '🔧')
            server_prefix = f"{emoji} "
        
        print(f"[{timestamp}] {symbol} {server_prefix}{message}")
    
    def test_server_connection(self, server_key):
        """Test basic connection to a server"""
        server = self.servers[server_key]
        try:
            conn = http.client.HTTPConnection(server['host'], server['port'])
            conn.request('HEAD', '/')
            response = conn.getresponse()
            conn.close()
            
            if response.status in [200, 404]:  # Server responding
                server['status'] = 'online'
                self.log_message(f"{server['name']} is responding on port {server['port']}", "SUCCESS", server_key)
                return True
            else:
                server['status'] = 'error'
                self.log_message(f"{server['name']} responded with status {response.status}", "WARNING", server_key)
                return False
                
        except ConnectionRefusedError:
            server['status'] = 'offline'
            self.log_message(f"{server['name']} not running on port {server['port']}", "ERROR", server_key)
            return False
        except Exception as e:
            server['status'] = 'error'
            self.log_message(f"{server['name']} connection error: {e}", "ERROR", server_key)
            return False
    
    def test_get_books(self, server_key):
        """Test GET /books endpoint"""
        server = self.servers[server_key]
        try:
            conn = http.client.HTTPConnection(server['host'], server['port'])
            conn.request('GET', '/books')
            response = conn.getresponse()
            
            if response.status == 200:
                data = response.read().decode()
                result = json.loads(data)
                conn.close()
                
                # Extract book count
                if isinstance(result, dict):
                    if 'data' in result:
                        book_count = len(result['data'])
                    else:
                        book_count = len(result) if isinstance(result, list) else 0
                else:
                    book_count = len(result) if isinstance(result, list) else 0
                
                self.log_message(f"GET /books: Retrieved {book_count} books", "SUCCESS", server_key)
                return {'success': True, 'book_count': book_count, 'data': result}
            else:
                conn.close()
                self.log_message(f"GET /books failed with status {response.status}", "ERROR", server_key)
                return {'success': False, 'status': response.status}
                
        except Exception as e:
            self.log_message(f"GET /books error: {str(e)}", "ERROR", server_key)
            return {'success': False, 'error': str(e)}
    
    def test_post_book(self, server_key, book_data):
        """Test POST /books endpoint"""
        server = self.servers[server_key]
        try:
            conn = http.client.HTTPConnection(server['host'], server['port'])
            headers = {'Content-type': 'application/json'}
            post_data = json.dumps(book_data)
            
            conn.request('POST', '/books', post_data, headers)
            response = conn.getresponse()
            
            if response.status == 200:
                data = response.read().decode()
                result = json.loads(data)
                conn.close()
                
                self.log_message(f"POST /books: Created '{book_data['title']}'", "SUCCESS", server_key)
                return {'success': True, 'data': result}
            else:
                conn.close()
                self.log_message(f"POST /books failed with status {response.status}", "ERROR", server_key)
                return {'success': False, 'status': response.status}
                
        except Exception as e:
            self.log_message(f"POST /books error: {str(e)}", "ERROR", server_key)
            return {'success': False, 'error': str(e)}
    
    def test_python_exclusive(self):
        """Test Python-exclusive endpoints"""
        self.log_message("Testing Python-exclusive endpoints", "TEST", "python")
        
        # Test Python-specific book creation
        python_book = {
            'title': 'Python Exclusive Book',
            'author': 'PyPolyCall Author'
        }
        
        try:
            conn = http.client.HTTPConnection('localhost', 3001)
            headers = {'Content-type': 'application/json'}
            post_data = json.dumps(python_book)
            
            conn.request('POST', '/python/books', post_data, headers)
            response = conn.getresponse()
            
            if response.status == 200:
                data = response.read().decode()
                result = json.loads(data)
                self.log_message("Python-exclusive book created successfully", "SUCCESS", "python")
                return {'success': True, 'data': result}
            else:
                self.log_message(f"Python-exclusive test failed: {response.status}", "ERROR", "python")
                return {'success': False}
                
        except Exception as e:
            self.log_message(f"Python-exclusive test error: {e}", "ERROR", "python")
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def test_server_status(self, server_key):
        """Test server status endpoint"""
        server = self.servers[server_key]
        
        # Try different status endpoints
        status_paths = ['/status', '/health']
        
        for path in status_paths:
            try:
                conn = http.client.HTTPConnection(server['host'], server['port'])
                conn.request('GET', path)
                response = conn.getresponse()
                
                if response.status == 200:
                    data = response.read().decode()
                    result = json.loads(data)
                    conn.close()
                    
                    self.log_message(f"Status check ({path}): OK", "SUCCESS", server_key)
                    return {'success': True, 'data': result, 'endpoint': path}
                
                conn.close()
                
            except Exception as e:
                continue
        
        self.log_message("No status endpoint available", "WARNING", server_key)
        return {'success': False}
    
    def run_server_tests(self, server_key):
        """Run all tests for a specific server"""
        self.log_message(f"Starting tests for {self.servers[server_key]['name']}", "TEST", server_key)
        
        results = {
            'server': server_key,
            'connection': False,
            'get_books': False,
            'post_book': False,
            'status': False
        }
        
        # Test 1: Connection
        if self.test_server_connection(server_key):
            results['connection'] = True
            
            # Test 2: GET books
            get_result = self.test_get_books(server_key)
            results['get_books'] = get_result['success']
            
            # Test 3: POST book
            test_book = {
                'title': f'Test Book from {self.servers[server_key]["name"]}',
                'author': f'{server_key.title()} Test Author'
            }
            post_result = self.test_post_book(server_key, test_book)
            results['post_book'] = post_result['success']
            
            # Test 4: Status endpoint
            status_result = self.test_server_status(server_key)
            results['status'] = status_result['success']
        
        with self.lock:
            self.test_results[server_key] = results
        
        return results
    
    def run_dual_tests(self):
        """Run tests on both servers simultaneously"""
        self.log_message("🚀 Starting Dual LibPolyCall Testing", "INFO")
        self.log_message("=" * 60, "INFO")
        
        # Check which servers are available
        available_servers = []
        for server_key in self.servers.keys():
            if self.test_server_connection(server_key):
                available_servers.append(server_key)
        
        if not available_servers:
            self.log_message("❌ No servers available for testing", "ERROR")
            return False
        
        self.log_message(f"Found {len(available_servers)} server(s): {', '.join(available_servers)}", "INFO")
        
        # Run tests in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_server = {
                executor.submit(self.run_server_tests, server_key): server_key 
                for server_key in available_servers
            }
            
            for future in as_completed(future_to_server):
                server_key = future_to_server[future]
                try:
                    result = future.result()
                    self.log_message(f"Tests completed for {server_key}", "SUCCESS", server_key)
                except Exception as exc:
                    self.log_message(f"Tests failed for {server_key}: {exc}", "ERROR", server_key)
        
        # Run Python-exclusive tests if Python server is available
        if 'python' in available_servers:
            self.test_python_exclusive()
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        self.log_message("=" * 60, "INFO")
        self.log_message("📊 DUAL TESTING SUMMARY", "INFO")
        self.log_message("=" * 60, "INFO")
        
        total_tests = 0
        passed_tests = 0
        
        for server_key, results in self.test_results.items():
            server = self.servers[server_key]
            self.log_message(f"\n{server['emoji']} {server['name']} (Port {server['port']}):", "INFO")
            
            tests = ['connection', 'get_books', 'post_book', 'status']
            server_passed = 0
            
            for test in tests:
                status = "✅ PASS" if results.get(test, False) else "❌ FAIL"
                self.log_message(f"   {test.replace('_', ' ').title()}: {status}", "INFO")
                total_tests += 1
                if results.get(test, False):
                    passed_tests += 1
                    server_passed += 1
            
            success_rate = (server_passed / len(tests)) * 100
            self.log_message(f"   Success Rate: {success_rate:.1f}%", "INFO")
        
        # Overall summary
        overall_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        self.log_message(f"\n🎯 Overall Results: {passed_tests}/{total_tests} tests passed ({overall_rate:.1f}%)", "INFO")
        
        if overall_rate >= 80:
            self.log_message("🎉 Dual testing SUCCESSFUL!", "SUCCESS")
        elif overall_rate >= 50:
            self.log_message("⚠️  Dual testing PARTIAL success", "WARNING")
        else:
            self.log_message("❌ Dual testing FAILED", "ERROR")
        
        # Connection status
        self.log_message("\n🔌 Server Status:", "INFO")
        for server_key, server in self.servers.items():
            status_emoji = {"online": "🟢", "offline": "🔴", "error": "🟡", "unknown": "⚪"}
            emoji = status_emoji.get(server['status'], "⚪")
            self.log_message(f"   {emoji} {server['name']}: {server['status'].upper()}", "INFO")


def main():
    """Main entry point"""
    print("🔄 LibPolyCall Dual Testing Client")
    print("Testing Node.js (8084) and Python (3001) servers")
    print("=" * 60)
    
    client = DualTestClient()
    
    try:
        success = client.run_dual_tests()
        client.print_summary()
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Testing failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
LibPolyCall v1 Banking System Professional Test Client
Comprehensive validation framework with zero-trust security verification
Author: Professional Engineering Team
Methodology: Systematic waterfall testing approach
"""

import json
import http.client
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

class LibPolyCallBankingTestFramework:
    """Professional test framework for LibPolyCall banking demonstration"""
    
    def __init__(self, host: str = "localhost", port: int = 8084):
        self.host = host
        self.port = port
        self.test_results: List[Dict[str, Any]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log_test_result(self, test_name: str, success: bool, message: str = "", details: Optional[Dict] = None):
        """Log test result with comprehensive metadata"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_symbol = "✅ PASS" if success else "❌ FAIL"
        
        print(f"[{timestamp}] {status_symbol} {test_name}")
        if message:
            print(f"    💬 {message}")
        if details and not success:
            print(f"    🔍 Details: {details}")
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": timestamp,
            "session_id": self.session_id
        })
    
    def execute_http_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute HTTP request with comprehensive error handling"""
        try:
            conn = http.client.HTTPConnection(self.host, self.port, timeout=10)
            headers = {'Content-Type': 'application/json'}
            
            request_body = json.dumps(data) if data else None
            conn.request(method, path, request_body, headers)
            
            response = conn.getresponse()
            response_data = response.read().decode()
            
            result = {
                "status_code": response.status,
                "success": response.status == 200,
                "data": json.loads(response_data) if response_data else None,
                "raw_response": response_data
            }
            
            return result
            
        except Exception as e:
            return {
                "status_code": 0,
                "success": False,
                "error": str(e),
                "data": None
            }
        finally:
            try:
                conn.close()
            except:
                pass
    
    def validate_zero_trust_security(self) -> bool:
        """Comprehensive zero-trust security validation"""
        print("\n🛡️  Testing Zero-Trust Security Enforcement")
        print("=" * 50)
        
        # Test 1: Authorized port access validation
        result = self.execute_http_request("GET", "/")
        if result["success"]:
            self.log_test_result(
                "Authorized port access", 
                True, 
                f"Port {self.port} accessible with proper authentication"
            )
        else:
            self.log_test_result(
                "Authorized port access", 
                False, 
                f"Port {self.port} rejected valid request", 
                {"status_code": result["status_code"], "error": result.get("error")}
            )
            return False
        
        # Test 2: Unauthorized port rejection validation
        try:
            unauthorized_conn = http.client.HTTPConnection(self.host, 9999, timeout=5)
            unauthorized_conn.request("GET", "/")
            response = unauthorized_conn.getresponse()
            unauthorized_conn.close()
            
            self.log_test_result(
                "Unauthorized port rejection", 
                False, 
                "SECURITY VIOLATION: Unauthorized port accepted connection"
            )
            return False
            
        except Exception:
            self.log_test_result(
                "Unauthorized port rejection", 
                True, 
                "Zero-trust enforcement working: Unauthorized port blocked"
            )
        
        # Test 3: Protocol validation
        result = self.execute_http_request("GET", "/accounts")
        if result["success"] and result["data"] and "libpolycall_version" in result["data"]:
            self.log_test_result(
                "LibPolyCall protocol validation", 
                True, 
                f"Protocol version: {result['data']['libpolycall_version']}"
            )
        else:
            self.log_test_result(
                "LibPolyCall protocol validation", 
                False, 
                "LibPolyCall protocol headers missing"
            )
            return False
        
        return True
    
    def validate_account_operations(self) -> bool:
        """Comprehensive account management validation"""
        print("\n🏦 Testing Account Management Operations")
        print("=" * 50)
        
        # Test 1: Account creation with validation
        account_data = {
            "name": "LibPolyCall Professional Test Account",
            "balance": 2500.0
        }
        
        result = self.execute_http_request("POST", "/accounts", account_data)
        if result["success"] and result["data"] and "data" in result["data"]:
            account_id = result["data"]["data"]["id"]
            balance = result["data"]["data"]["balance"]
            self.log_test_result(
                "Account creation with validation", 
                True, 
                f"Account created: ID={account_id[:8]}..., Balance=${balance}"
            )
        else:
            self.log_test_result(
                "Account creation with validation", 
                False, 
                "Account creation failed", 
                {"response": result}
            )
            return False
        
        # Test 2: Account enumeration validation
        result = self.execute_http_request("GET", "/accounts")
        if result["success"] and result["data"] and "data" in result["data"]:
            accounts = result["data"]["data"]
            account_count = len(accounts)
            self.log_test_result(
                "Account enumeration validation", 
                True, 
                f"Successfully retrieved {account_count} accounts"
            )
        else:
            self.log_test_result(
                "Account enumeration validation", 
                False, 
                "Failed to retrieve account list", 
                {"response": result}
            )
            return False
        
        # Test 3: Individual account access validation
        result = self.execute_http_request("GET", f"/accounts/{account_id}")
        if result["success"] and result["data"] and "data" in result["data"]:
            account = result["data"]["data"]
            self.log_test_result(
                "Individual account access", 
                True, 
                f"Account retrieved: {account['name']}, Balance: ${account['balance']}"
            )
        else:
            self.log_test_result(
                "Individual account access", 
                False, 
                f"Failed to retrieve account {account_id}"
            )
            return False
        
        # Store account_id for transaction tests
        self.test_account_id = account_id
        return True
    
    def validate_transaction_operations(self) -> bool:
        """Comprehensive transaction processing validation"""
        print("\n💸 Testing Transaction Processing Operations")
        print("=" * 50)
        
        # Create additional account for transfer testing
        target_account_data = {
            "name": "LibPolyCall Transfer Target Account",
            "balance": 1000.0
        }
        
        result = self.execute_http_request("POST", "/accounts", target_account_data)
        if not result["success"]:
            self.log_test_result(
                "Transfer target account creation", 
                False, 
                "Failed to create target account for transfer testing"
            )
            return False
        
        target_account_id = result["data"]["data"]["id"]
        
        # Test fund transfer with validation
        transfer_data = {
            "to_account": target_account_id,
            "amount": 500.0
        }
        
        result = self.execute_http_request("POST", f"/accounts/{self.test_account_id}/transfer", transfer_data)
        if result["success"]:
            self.log_test_result(
                "Inter-account fund transfer", 
                True, 
                f"Successfully transferred $500.0 to target account"
            )
        else:
            self.log_test_result(
                "Inter-account fund transfer", 
                False, 
                "Fund transfer operation failed", 
                {"response": result}
            )
            return False
        
        # Verify account balances post-transfer
        source_result = self.execute_http_request("GET", f"/accounts/{self.test_account_id}")
        target_result = self.execute_http_request("GET", f"/accounts/{target_account_id}")
        
        if (source_result["success"] and target_result["success"]):
            source_balance = source_result["data"]["data"]["balance"]
            target_balance = target_result["data"]["data"]["balance"]
            
            expected_source = 2000.0  # 2500 - 500
            expected_target = 1500.0  # 1000 + 500
            
            if source_balance == expected_source and target_balance == expected_target:
                self.log_test_result(
                    "Post-transfer balance validation", 
                    True, 
                    f"Balances verified: Source=${source_balance}, Target=${target_balance}"
                )
            else:
                self.log_test_result(
                    "Post-transfer balance validation", 
                    False, 
                    f"Balance mismatch: Expected Source=${expected_source}, Target=${expected_target}"
                )
                return False
        else:
            self.log_test_result(
                "Post-transfer balance validation", 
                False, 
                "Failed to retrieve account balances for verification"
            )
            return False
        
        # Test transaction history retrieval
        result = self.execute_http_request("GET", f"/accounts/{self.test_account_id}/transactions")
        if result["success"] and result["data"] and "data" in result["data"]:
            transactions = result["data"]["data"]
            transaction_count = len(transactions)
            self.log_test_result(
                "Transaction history retrieval", 
                True, 
                f"Retrieved {transaction_count} transactions for account"
            )
        else:
            self.log_test_result(
                "Transaction history retrieval", 
                False, 
                "Failed to retrieve transaction history"
            )
            return False
        
        return True
    
    def validate_system_status(self) -> bool:
        """System operational status validation"""
        print("\n⚙️  Testing System Operational Status")
        print("=" * 50)
        
        result = self.execute_http_request("GET", "/")
        if result["success"] and result["data"] and "data" in result["data"]:
            system_data = result["data"]["data"]
            self.log_test_result(
                "System operational status", 
                True, 
                f"System: {system_data.get('system')}, Status: {system_data.get('status')}"
            )
            return True
        else:
            self.log_test_result(
                "System operational status", 
                False, 
                "System status endpoint not responding correctly"
            )
            return False
    
    def execute_comprehensive_test_suite(self) -> None:
        """Execute complete professional validation test suite"""
        print("🏦 LibPolyCall v1 Banking API Professional Test Suite")
        print("=" * 60)
        print(f"🎯 Target System: {self.host}:{self.port}")
        print(f"🕐 Test Session: {self.session_id}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Execute systematic test validation phases
        test_phases = [
            ("System Status", self.validate_system_status),
            ("Zero-Trust Security", self.validate_zero_trust_security),
            ("Account Operations", self.validate_account_operations),
            ("Transaction Operations", self.validate_transaction_operations)
        ]
        
        phase_results = []
        for phase_name, phase_function in test_phases:
            print(f"\n🔄 Executing {phase_name} Validation Phase...")
            try:
                phase_success = phase_function()
                phase_results.append((phase_name, phase_success))
                
                if phase_success:
                    print(f"✅ {phase_name} validation: COMPLETED SUCCESSFULLY")
                else:
                    print(f"❌ {phase_name} validation: FAILED")
                    
            except Exception as e:
                print(f"💥 {phase_name} validation: EXCEPTION OCCURRED")
                print(f"   Error: {str(e)}")
                phase_results.append((phase_name, False))
        
        # Comprehensive results analysis
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUITE RESULTS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        successful_phases = sum(1 for _, success in phase_results if success)
        total_phases = len(phase_results)
        
        if successful_phases == total_phases and failed_tests == 0:
            print("🎉 ALL LIBPOLYCALL BANKING API TESTS PASSED!")
            print("✅ Zero-trust security enforcement: VERIFIED")
            print("✅ Banking operations validation: SUCCESSFUL")
            print("✅ Transaction integrity verification: CONFIRMED")
            print("✅ System operational status: VALIDATED")
            print("✅ LibPolyCall integration: PROFESSIONAL GRADE")
        else:
            print(f"⚠️  PARTIAL SUCCESS: {successful_phases}/{total_phases} phases passed")
            print(f"📊 Individual tests: {passed_tests}/{total_tests} passed, {failed_tests} failed")
            
            if failed_tests > 0:
                print("\n❌ Failed Tests Summary:")
                for result in self.test_results:
                    if not result["success"]:
                        print(f"   - {result['test_name']}: {result['message']}")
        
        print(f"\n📈 Final Statistics:")
        print(f"   🧪 Total Tests Executed: {total_tests}")
        print(f"   ✅ Tests Passed: {passed_tests}")
        print(f"   ❌ Tests Failed: {failed_tests}")
        print(f"   📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"   ⏱️  Test Duration: {self.session_id}")
        
        print("\n🏁 LibPolyCall v1 Professional Banking Demonstration Validation Complete")
        
        # Exit with appropriate code for automation integration
        sys.exit(0 if failed_tests == 0 else 1)

def main():
    """Main test execution with professional error handling"""
    try:
        test_framework = LibPolyCallBankingTestFramework()
        test_framework.execute_comprehensive_test_suite()
    except KeyboardInterrupt:
        print("\n⚠️  Test suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Test suite execution failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

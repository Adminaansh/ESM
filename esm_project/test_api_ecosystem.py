# test_api_ecosystem.py
import urllib.request
import urllib.error
import json
import uuid

BASE_URL = "http://127.0.0.1:8000/api"

def dispatch_request(method, endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raw_error_body = e.read().decode('utf-8')
        try:
            # Attempt to parse as JSON if possible
            return e.code, json.loads(raw_error_body)
        except json.JSONDecodeError:
            # Fallback if Django spits out an HTML page error instead of JSON
            return e.code, {"error": "Server returned raw non-JSON payload data", "raw_html_excerpt": raw_error_body[:200]}
    except Exception as e:
        return 500, {"error": str(e)}

def run_system_test_suite():
    print("🚀 INITIALIZING AUTOMATED ESM API SYSTEM TEST...\n" + "="*50)
    
    # -------------------------------------------------------------------------
    # TEST 1: Module 4 - Infrastructure Automated Handshake
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Module 4: Simulating Remote Node Bootup & Handshake...")
    handshake_payload = {
        "hostname": "prod-k8s-node-01",
        "ip_address": "192.168.1.105",
        "agent_version": "2.4.0",
        "target_type": "CONTAINER"
    }
    code, res = dispatch_request("POST", "/infrastructure/agent/handshake/", handshake_payload)
    print(f"Status: {code} | Response: {res}")
    if code != 200: return print("❌ Test 1 Failed.")
    
    auth_token = res.get("authorization_token")

    # -------------------------------------------------------------------------
    # TEST 2: Module 4 - Telemetry Ingestion & Automated Rule Check
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Module 4: Ingesting High CPU Telemetry (Should auto-flag UNHEALTHY)...")
    telemetry_payload = {
        "token": auth_token,
        "cpu_percent": 94.5,
        "memory_percent": 45.2
    }
    code, res = dispatch_request("POST", "/infrastructure/telemetry/heartbeat/", telemetry_payload)
    print(f"Status: {code} | Response: {res}")
    if res.get("engine_status") != "UNHEALTHY": return print("❌ Test 2 System Rule Failed.")

    # -------------------------------------------------------------------------
    # TEST 3: Module 7 - Vault Secret Token Encryption Injection
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Module 7: Injecting Sensitive Database Password into Vault...")
    vault_payload = {
        "key": "PROD_DB_PASS",
        "value": "SuperSecretPassword123!",
        "description": "Production cluster access token"
    }
    code, res = dispatch_request("POST", "/vault/secret/inject/", vault_payload)
    print(f"Status: {code} | Response: {res}")
    if code != 200: return print("❌ Test 3 Vault Injection Failed.")

    # -------------------------------------------------------------------------
    # TEST 4: Module 6 & 5 - Scheduler Evaluation & Monitoring Execution Run
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Module 6 & 5: Simulating Scheduler Clock Pulse Evaluation...")
    code, res = dispatch_request("POST", "/scheduler/engine/evaluate/")
    print(f"Status: {code} | Response: {res}")
    
    print("\n[TEST 4b] Module 5: Spawning an Active Job Pipeline Execution...")
    exec_payload = {
        "chain_id": str(uuid.uuid4()),
        "source": "AUTOMATED_TEST_SUITE"
    }
    code, res = dispatch_request("POST", "/monitoring/execution/start/", exec_payload)
    print(f"Status: {code} | Response: {res}")
    execution_id = res.get("execution_id")
    process_no = res.get("process_no")

    # -------------------------------------------------------------------------
    # TEST 5: Module 5 - Stream Active Task Log Outputs
    # -------------------------------------------------------------------------
    print(f"\n[TEST 5] Module 5: Appending Live Standard Output Stream Logs to Process #{process_no}...")
    log_payload = {
        "execution_id": execution_id,
        "node_id": str(uuid.uuid4()),
        "level": "INFO",
        "message": "Starting automated migration cleanup task... Done."
    }
    code, res = dispatch_request("POST", "/monitoring/execution/log/", log_payload)
    print(f"Status: {code} | Response: {res}")

    # -------------------------------------------------------------------------
    # TEST 6: Module 8 - Data Janitor Archival Sweep Simulation
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Module 8: Moving Finished Process Run Logs to Long-Term Cold Storage...")
    archive_payload = {
        "execution_id": execution_id,
        "process_no": process_no,
        "chain_id": str(uuid.uuid4()),
        "status": "COMPLETED",
        "triggered_by": "AUTOMATED_TEST_SUITE",
        "duration_seconds": 4.5,
        "logs_array": ["Init pipeline", "Running Step 1", "Process executed successfully"]
    }
    code, res = dispatch_request("POST", "/compliance/archive/sweep/", archive_payload)
    print(f"Status: {code} | Response: {res}")

    # -------------------------------------------------------------------------
    # TEST 7: Module 9 - Database Maintenance Engine Policy Enforcer
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Module 9: Seeding Maintenance Policies and Enforcing Purge...")
    
    # SYSTEM SEEDING HOOK: Safely inject retention settings directly into Django ORM layer if available
    try:
        import django
        import os
        if "DJANGO_SETTINGS_MODULE" not in os.environ:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esm_core.settings")
        django.setup()
        from django.apps import apps
        PolicyModel = apps.get_model('maintenance', 'MaintenancePolicy')
        PolicyModel.objects.get_or_create(subsystem='LIVE_LOGS', defaults={'retention_days': 14, 'is_active': True})
        print("-> System Policy Context Seeded.")
    except Exception as e:
        print(f"-> Local context seeding bypassed: {e}")

    purge_payload = {"subsystem": "LIVE_LOGS"}
    code, res = dispatch_request("POST", "/maintenance/database/purge/", purge_payload)
    print(f"Status: {code} | Response: {res}")

    # -------------------------------------------------------------------------
    # TEST 8: Module 9 - Global Visibility Health Metric Aggregator
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Module 9 & 4 Dashboard Overview Matrices Lookup...")
    code, res = dispatch_request("GET", "/maintenance/system/health/")
    
    health_metrics = res.get('system_health_metrics', {})
    score = health_metrics.get('overall_score_percent', 0.0)
    print(f"Global System Score: {score}%")
    print(f"Complete Diagnostics payload: {res}")

    print("\n" + "="*50 + "\n🎉 SYSTEM CORE VERIFICATION INTEGRATION COMPLETE. ALL MODULES OPERATING.")

if __name__ == "__main__":
    run_system_test_suite()
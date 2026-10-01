#!/usr/bin/env python
"""
Test script to verify job execution fix:
1. Create a chain with the Pune weather job
2. Start execution
3. Monitor for completion and output
"""
import os
import sys
import django
import time
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esm_core.settings')
django.setup()

from studio.models import JobObject
from engine.models import Chain, ChainNode
from monitoring.models import WorkflowExecution, WorkflowExecutionHistory, LiveExecutionLog
from execution_hub.services import ExecutionHubService

def test_job_execution():
    print("=" * 80)
    print("TEST: Job Execution Fix Verification")
    print("=" * 80)
    
    # Step 1: Get or create the Pune weather job
    print("\n[STEP 1] Getting Pune weather job...")
    job, created = JobObject.objects.get_or_create(
        name="PUNE_WEATHER_FETCH",
        defaults={
            "description": "Fetch weather information for Pune",
            "script_content": """import urllib.request
import json

try:
    url = 'https://wttr.in/Pune?format=j1'
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        current = data['current_condition'][0]
        print(f"Temperature: {current.get('temp_C', 'N/A')}°C")
        print(f"Description: {current.get('weatherDesc', [{}])[0].get('value', 'N/A')}")
        print(f"Humidity: {current.get('humidity', 'N/A')}%")
except Exception as e:
    print(f"Error fetching weather: {e}")
""",
            "is_active": True,
            "version": 1
        }
    )
    status = "created" if created else "already exists"
    print(f"✓ Job '{job.name}' {status}")
    print(f"  Job ID: {job.id}")
    
    # Step 2: Create a test chain
    print("\n[STEP 2] Creating test chain...")
    chain_name = f"TEST_WEATHER_CHAIN_{int(time.time())}"
    chain = Chain.objects.create(
        name=chain_name,
        description="Test chain for weather job execution",
        chain_code=int(time.time()) % 1000000  # Simple 6-digit code
    )
    print(f"✓ Chain created: {chain.name}")
    print(f"  Chain ID: {chain.id}")
    print(f"  Chain Code: {chain.chain_code}")
    
    # Step 3: Add the job as a node
    print("\n[STEP 3] Adding job node to chain...")
    node = ChainNode.objects.create(
        chain=chain,
        job=job,
        pos_x=0,
        pos_y=0
    )
    print(f"✓ Node created with job")
    print(f"  Node ID: {node.id}")
    
    # Step 4: Start execution
    print("\n[STEP 4] Starting job execution...")
    execution = ExecutionHubService.run_job(chain.chain_code, source="TEST_SCRIPT")
    print(f"✓ Execution started")
    print(f"  Process #: {execution.process_no}")
    print(f"  Execution ID: {execution.id}")
    print(f"  Status: {execution.status}")
    
    # Step 5: Monitor execution
    print("\n[STEP 5] Monitoring execution (waiting 10 seconds)...")
    start_time = time.time()
    max_wait = 10
    
    while time.time() - start_time < max_wait:
        execution.refresh_from_db()
        print(f"  Status: {execution.status}")
        
        if execution.status in ('COMPLETED', 'FAILED'):
            print(f"✓ Execution {execution.status}")
            break
        
        time.sleep(1)
    
    # Step 6: Check live logs
    print("\n[STEP 6] Checking live execution logs...")
    logs = list(execution.logs.all().order_by('timestamp'))
    if logs:
        print(f"✓ Found {len(logs)} log entries:")
        for log in logs:
            print(f"  [{log.log_level}] {log.message}")
    else:
        print("  No logs found")
    
    # Step 7: Check execution history
    print("\n[STEP 7] Checking execution history...")
    history = WorkflowExecutionHistory.objects.filter(process_no=execution.process_no).first()
    if history:
        print(f"✓ History record found")
        print(f"  Status: {history.status}")
        print(f"  Compiled output:")
        if history.compiled_console_output:
            for line in history.compiled_console_output.split('\n')[:10]:  # First 10 lines
                print(f"    {line}")
        else:
            print("    (no output)")
    else:
        print("  No history record found")
    
    # Step 8: Verify execution still in live monitoring
    print("\n[STEP 8] Verifying execution in live monitoring...")
    live_exec = WorkflowExecution.objects.filter(id=execution.id).first()
    if live_exec:
        print(f"✓ Execution still in live table")
        print(f"  Current status: {live_exec.status}")
    else:
        print("✗ Execution NOT in live table (was deleted)")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return {
        "chain": chain,
        "execution": execution,
        "history": history,
        "live": live_exec is not None
    }

if __name__ == "__main__":
    try:
        results = test_job_execution()
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

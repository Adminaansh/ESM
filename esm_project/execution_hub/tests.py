import os
import time
from django.contrib.auth import get_user_model
from django.test import TestCase

from engine.models import Chain, ChainNode
from monitoring.models import WorkflowExecution
from studio.models import JobObject, ScriptRevision
from execution_hub.services import ExecutionHubService

User = get_user_model()


class ExecutionHubServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='exec_test_user', password='testpass')

    def test_execute_script_locally_returns_stdout(self):
        if os.name == 'nt':
            script = 'Write-Output "HELLO_EXEC"'
            platform_name = 'WINDOWS'
        else:
            script = 'echo "HELLO_EXEC"'
            platform_name = 'UNIX'

        result = ExecutionHubService._execute_script_locally(script, platform_name)
        self.assertEqual(result.returncode, 0)
        self.assertIn('HELLO_EXEC', result.stdout.decode('utf-8'))

    def test_job_script_content_runs_during_chain_execution(self):
        platform_name = 'WINDOWS' if os.name == 'nt' else 'UNIX'
        script = 'Write-Output "CHAIN_RUN_OK"' if os.name == 'nt' else 'echo "CHAIN_RUN_OK"'

        job = JobObject.objects.create(
            name='TEST_EXECUTION_JOB',
            title='Execution test job',
            platform=platform_name,
            is_active=True,
            owner=self.user
        )
        ScriptRevision.objects.create(
            job_object=job,
            version=1,
            content=script,
            created_by=self.user
        )

        chain = Chain.objects.create(
            name=f'TEST_EXECUTION_CHAIN_{int(time.time())}',
            description='Chain for execution service test',
            chain_code=999999
        )
        ChainNode.objects.create(chain=chain, job=job)

        execution = WorkflowExecution.objects.create(
            chain_id=str(chain.chain_code),
            status='RUNNING',
            triggered_by='TEST_SCRIPT'
        )
        ExecutionHubService._run_chain_steps(str(execution.id), str(chain.chain_code))

        execution.refresh_from_db()
        self.assertEqual(execution.status, 'COMPLETED')
        logs = execution.logs.filter(log_level='INFO')
        self.assertTrue(any('CHAIN_RUN_OK' in log.message for log in logs), 'Expected execution output to appear in live logs')

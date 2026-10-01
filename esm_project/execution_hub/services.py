import threading
import time
import logging
import tempfile
import subprocess
import os
import json
import urllib.request
import urllib.error
from types import SimpleNamespace
from django.db import DatabaseError, close_old_connections
from django.utils import timezone
from monitoring.models import WorkflowExecution, WorkflowExecutionStep, LiveExecutionLog, ExternalAPITracking
from engine.models import Chain
from engine.execution_manager import execution_manager

logger = logging.getLogger(__name__)

class ExecutionHubService:
    # --- Lifecycle ---
    @staticmethod
    def _resolve_chain(chain_id):
        if chain_id is None:
            return None
        # If numeric (or numeric string) treat as chain_code
        if isinstance(chain_id, int) or (isinstance(chain_id, str) and str(chain_id).isdigit()):
            try:
                return Chain.objects.get(chain_code=int(chain_id))
            except Chain.DoesNotExist:
                return None

        # Try UUID-style chain_guid lookup (accepts hyphenated or compact hex strings)
        try:
            from uuid import UUID
            # Normalize and validate UUID
            guid = None
            try:
                guid = UUID(str(chain_id))
            except Exception:
                # Attempt to handle compact hex string by inserting dashes via UUID constructor
                try:
                    guid = UUID(str(chain_id))
                except Exception:
                    guid = None

            if guid:
                try:
                    return Chain.objects.get(chain_guid=guid)
                except Chain.DoesNotExist:
                    # Try lenient contains lookup (handles compact hex or stored without dashes)
                    try:
                        return Chain.objects.filter(chain_guid__icontains=str(chain_id)).first()
                    except Exception:
                        return None
        except Exception:
            # Fallthrough if UUID not applicable
            return None

        return None

    @staticmethod
    def _archive_execution(execution):
        from monitoring.models import WorkflowExecutionHistory

        chain_name = None
        try:
            chain = ExecutionHubService._resolve_chain(execution.chain_id)
            chain_name = chain.name if chain else None
        except Exception:
            chain_name = None

        console_lines = []
        for log in execution.logs.all():
            timestamp = log.timestamp.isoformat() if log.timestamp else 'unknown-time'
            console_lines.append(f"{timestamp} [{log.log_level}] {log.message}")
        compiled_output = "\n".join(console_lines)

        WorkflowExecutionHistory.objects.create(
            original_execution_id=execution.id,
            process_no=execution.process_no,
            chain_id=str(execution.chain_id),
            chain_name=chain_name,
            task_name=chain_name or execution.triggered_by,
            source=execution.triggered_by,
            status=execution.status,
            started_at=execution.started_at,
            ended_at=execution.ended_at,
            compiled_console_output=compiled_output,
        )
        # Keep execution visible in live monitoring - don't delete immediately
        # Users need to see jobs completed before they disappear from the UI
        logger.info(f"Execution {execution.id} (process #{execution.process_no}) archived to history but kept in live table for visibility")

    @staticmethod
    def run_job(chain_id, source="API"):
        chain = ExecutionHubService._resolve_chain(chain_id)
        if not chain:
            logger.error(f"Chain {chain_id} not found during run_job")
            raise ValueError("Chain reference not found")

        logger.info(f"Creating execution for chain {chain.name} (code={chain.chain_code})")
        attempt = 0
        while True:
            try:
                close_old_connections()
                execution = WorkflowExecution.objects.create(chain_id=str(chain.chain_code), status="RUNNING", triggered_by=source)
                break
            except DatabaseError as exc:
                if attempt >= 4 or 'locked' not in str(exc).lower():
                    raise
                attempt += 1
                logger.warning('SQLite locked during execution create, retrying attempt %s...', attempt)
                time.sleep(0.2 * attempt)

        logger.info(f"Execution created: Process #{execution.process_no}, ID={execution.id}")
        
        thread = threading.Thread(target=ExecutionHubService._run_chain_steps, args=(str(execution.id), str(chain.chain_code)), daemon=True, name=f"ChainRunner-{execution.process_no}")
        thread.start()
        logger.info(f"Execution thread started for process #{execution.process_no}")
        return execution

    @staticmethod
    def _run_chain_steps(execution_id, chain_id):
        try:
            execution = WorkflowExecution.objects.get(id=execution_id)
        except WorkflowExecution.DoesNotExist:
            logger.error(f"Execution {execution_id} not found")
            return

        try:
            logger.info(f"Starting execution chain for process #{execution.process_no} with chain_id={chain_id}")
            
            # Log execution start
            LiveExecutionLog.objects.create(
                execution=execution,
                node_id=None,
                log_level='INFO',
                message=f'[EXECUTION_START] Process #{execution.process_no} initiated with chain code {chain_id}'
            )

            chain = ExecutionHubService._resolve_chain(chain_id)
            if not chain:
                logger.error(f"Chain {chain_id} not found")
                execution.status = 'FAILED'
                execution.ended_at = timezone.now()
                execution.save()
                LiveExecutionLog.objects.create(
                    execution=execution,
                    node_id=None,
                    log_level='ERROR',
                    message=f'[ERROR] Chain reference {chain_id} not found'
                )
                logger.info(f"Archiving deferred for execution {execution.id} (chain not found); kept in live monitoring")
                return

            ordered_nodes = list(chain.nodes.all().order_by('pos_y', 'id'))
            logger.info(f"Chain {chain.name} has {len(ordered_nodes)} nodes")
            
            if not ordered_nodes:
                logger.warning(f"Chain {chain.name} has no nodes, completing immediately")
                LiveExecutionLog.objects.create(
                    execution=execution,
                    node_id=None,
                    log_level='WARNING',
                    message='[WARNING] Chain has no nodes, completing immediately'
                )
            
            for idx, node in enumerate(ordered_nodes):
                execution.refresh_from_db()
                if execution.status in ('TERMINATED', 'FAILED'):
                    break
                while execution.status == 'PAUSED':
                    time.sleep(1)
                    execution.refresh_from_db()
                    if execution.status in ('TERMINATED', 'FAILED'):
                        break
                if execution.status not in ('RUNNING', 'QUEUED'):
                    break

                logger.info(f"Executing step {idx}: {node.job.name}")
                
                step = WorkflowExecutionStep.objects.create(
                    execution=execution,
                    node_id=node.id,
                    job_name=node.job.name,
                    sequence_index=idx,
                    status='RUNNING',
                    started_at=timezone.now()
                )

                # Log step start
                LiveExecutionLog.objects.create(
                    execution=execution,
                    node_id=node.id,
                    log_level='INFO',
                    message=f'[STEP_{idx}_START] Job: {node.job.name}'
                )

                script_content = ExecutionHubService._get_job_script(node)
                if not script_content.strip():
                    step.status = 'FAILED'
                    step.ended_at = timezone.now()
                    step.save()
                    LiveExecutionLog.objects.create(
                        execution=execution,
                        node_id=node.id,
                        log_level='ERROR',
                        message=f'[STEP_{idx}_FAILED] No script found for job {node.job.name}'
                    )
                    execution.status = 'FAILED'
                    execution.ended_at = timezone.now()
                    execution.save()
                    break

                try:
                    result = ExecutionHubService._execute_script(node, step, script_content)

                    if result.returncode != 0:
                        break
                except Exception as exc:
                    logger.exception(f"Job step execution failed: {exc}")
                    step.status = 'FAILED'
                    step.ended_at = timezone.now()
                    step.save()
                    LiveExecutionLog.objects.create(
                        execution=execution,
                        node_id=node.id,
                        log_level='ERROR',
                        message=f'[STEP_{idx}_EXCEPTION] {str(exc)}'
                    )
                    execution.status = 'FAILED'
                    execution.ended_at = timezone.now()
                    execution.save()
                    break

            execution.refresh_from_db()
            if execution.status not in ('TERMINATED', 'FAILED'):
                execution.status = 'COMPLETED'
                execution.ended_at = timezone.now()
                execution.save()
                logger.info(f"Process #{execution.process_no} completed successfully")
                LiveExecutionLog.objects.create(
                    execution=execution,
                    node_id=None,
                    log_level='INFO',
                    message=f'[EXECUTION_COMPLETED] Process #{execution.process_no} completed successfully'
                )
            logger.info(f"Archiving deferred for execution {execution.id} after run completion; kept in live monitoring until user archives")
        except Exception as exc:
            logger.exception(f"Execution {execution_id} failed with exception: {exc}")
            execution.status = 'FAILED'
            execution.ended_at = timezone.now()
            execution.save()
            LiveExecutionLog.objects.create(
                execution=execution,
                node_id=None,
                log_level='ERROR',
                message=f'[EXECUTION_ERROR] {str(exc)}'
            )
            execution_manager.bypass_node_failure(execution.id)
            logger.info(f"Archiving deferred for execution {execution.id} after exception; kept in live monitoring until user archives")

    @staticmethod
    def _get_job_script(node):
        active_revision = node.job.revisions.filter(version=node.job.active_revision).first()
        if active_revision:
            return active_revision.content or ''
        latest_revision = node.job.revisions.order_by('-version').first()
        return latest_revision.content if latest_revision else ''

    @staticmethod
    def _execute_script(node, step, script_content):
        script_language = getattr(node.job, 'script_language', 'BASH')
        target = getattr(node, 'target', None)
        if target and target.target_type == 'LINUX_SERVER':
            return ExecutionHubService._execute_script_remote_linux(
                script_content,
                host=target.host_address,
                username=None,
                port=None,
                auth_method='NONE',
                secret=None,
                interpreter='python' if script_language == 'PYTHON' else 'bash'
            )

        if getattr(node.job, 'remote_host', ''):
            return ExecutionHubService._execute_script_remote_linux(
                script_content,
                host=node.job.remote_host,
                username=node.job.remote_username,
                port=node.job.remote_port,
                auth_method=node.job.remote_auth_method,
                secret=node.job.get_secret(),
                interpreter='python' if script_language == 'PYTHON' else 'bash'
            )

        platform_obj = getattr(node.job, 'platform_obj', None)
        if platform_obj and platform_obj.platform_type == 'API':
            return ExecutionHubService._execute_external_api(node, step, platform_obj)

        if platform_obj and platform_obj.platform_type == 'SSH' and platform_obj.host:
            return ExecutionHubService._execute_script_remote_linux(
                script_content,
                host=platform_obj.host,
                username=platform_obj.username,
                port=platform_obj.port,
                auth_method=platform_obj.auth_method,
                secret=platform_obj.get_secret(),
                interpreter='python' if script_language == 'PYTHON' else 'bash'
            )

        platform = platform_obj.code if platform_obj else node.job.platform
        return ExecutionHubService._execute_script_locally(script_content, platform, script_language)

    @staticmethod
    def _execute_external_api(node, step, platform_obj):
        from monitoring.models import ExternalAPITracking

        request_payload = platform_obj.api_body_template or ''
        headers = {}
        if platform_obj.api_headers:
            try:
                headers = json.loads(platform_obj.api_headers)
            except Exception:
                headers = {}

        if platform_obj.auth_method == 'PASSWORD' and platform_obj.secret_reference:
            token = platform_obj.get_secret()
            if token:
                headers.setdefault('Authorization', f'Bearer {token}')

        if request_payload and 'Content-Type' not in {k.title(): v for k, v in headers.items()}:
            headers.setdefault('Content-Type', 'application/json')

        url = platform_obj.api_url or platform_obj.host
        if not url:
            raise ValueError('External API platform is missing api_url or host configuration')

        method = (platform_obj.api_method or 'POST').upper()
        data = request_payload.encode('utf-8') if request_payload else None
        request_obj = urllib.request.Request(url, data=data, method=method)
        for header_name, header_value in headers.items():
            request_obj.add_header(header_name, header_value)

        response_code = None
        response_text = ''
        external_job_id = ''
        try:
            with urllib.request.urlopen(request_obj, timeout=30) as resp:
                response_code = resp.getcode()
                response_text = resp.read().decode('utf-8', errors='replace')
                if response_text:
                    try:
                        payload_data = json.loads(response_text)
                        external_job_id = payload_data.get('external_job_id') or payload_data.get('job_id') or payload_data.get('id') or ''
                    except Exception:
                        external_job_id = ''
        except urllib.error.HTTPError as exc:
            response_code = exc.code
            response_text = exc.read().decode('utf-8', errors='replace')
        except Exception as exc:
            response_code = 500
            response_text = str(exc)

        tracking = ExternalAPITracking.objects.create(
            step=step,
            external_job_id=external_job_id,
            status='RUNNING' if response_code in (200, 202) else 'FAILED',
            callback_secret=platform_obj.api_callback_secret or '',
            request_payload=request_payload,
            response_summary=response_text or f'HTTP {response_code}'
        )

        LiveExecutionLog.objects.create(
            execution=step.execution,
            node_id=node.id,
            log_level='INFO' if response_code in (200, 202) else 'ERROR',
            message=f'[EXTERNAL_API_START] {method} {url} -> status {response_code} callback_id={tracking.id}'
        )

        if response_code not in (200, 202):
            return SimpleNamespace(returncode=1, stdout=response_text.encode('utf-8'), stderr=response_text.encode('utf-8'))

        timeout_seconds = platform_obj.api_timeout_seconds if platform_obj.api_timeout_seconds and platform_obj.api_timeout_seconds > 0 else 600
        completed = ExecutionHubService._wait_for_external_api_completion(tracking, timeout_seconds)
        tracking.refresh_from_db()

        if completed and tracking.status == 'COMPLETED':
            LiveExecutionLog.objects.create(
                execution=step.execution,
                node_id=node.id,
                log_level='INFO',
                message=f'[EXTERNAL_API_COMPLETED] external_job_id={tracking.external_job_id} response={tracking.response_summary}'
            )
            return SimpleNamespace(returncode=0, stdout=tracking.response_summary.encode('utf-8'), stderr=b'')

        if tracking.status == 'FAILED':
            LiveExecutionLog.objects.create(
                execution=step.execution,
                node_id=node.id,
                log_level='ERROR',
                message=f'[EXTERNAL_API_FAILED] external_job_id={tracking.external_job_id} response={tracking.response_summary}'
            )
            return SimpleNamespace(returncode=1, stdout=b'', stderr=tracking.response_summary.encode('utf-8'))

        LiveExecutionLog.objects.create(
            execution=step.execution,
            node_id=node.id,
            log_level='ERROR',
            message=f'[EXTERNAL_API_TIMEOUT] external_job_id={tracking.external_job_id} waited {timeout_seconds}s'
        )
        tracking.status = 'TIMED_OUT'
        tracking.response_summary = 'Callback not received within timeout window.'
        tracking.save(update_fields=['status', 'response_summary'])
        return SimpleNamespace(returncode=1, stdout=b'', stderr=b'External API callback timed out')

    @staticmethod
    def _wait_for_external_api_completion(tracking, timeout_seconds):
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            tracking.refresh_from_db()
            if tracking.status in ('COMPLETED', 'FAILED'):
                return True
            time.sleep(2)
        return False

    @staticmethod
    def _execute_script_locally(script_content, platform, script_language='BASH'):
        suffix = '.sh'
        if platform == 'WINDOWS' and script_language == 'BASH':
            suffix = '.ps1'
        elif platform == 'WINDOWS' and script_language == 'PYTHON':
            suffix = '.py'
        elif platform == 'UNIX' and script_language == 'PYTHON':
            suffix = '.py'
        elif platform == 'SQL' or platform == 'SAP':
            raise ValueError(f"Unsupported script platform: {platform}")

        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix=suffix, encoding='utf-8') as tmp:
                tmp_file = tmp.name
                tmp.write(script_content)
            if platform == 'UNIX':
                os.chmod(tmp_file, 0o700)
                if script_language == 'PYTHON':
                    cmd = ['python3', tmp_file]
                else:
                    cmd = ['bash', tmp_file]
            elif platform == 'WINDOWS':
                if script_language == 'PYTHON':
                    cmd = ['python', tmp_file]
                else:
                    cmd = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', tmp_file]
            else:
                raise ValueError(f"Unsupported script platform: {platform}")

            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass

    @staticmethod
    def _execute_script_remote_linux(script_content, host, username=None, port=None, auth_method='NONE', secret=None, interpreter='bash'):
        tmp_key_file = None
        base_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null']
        if port:
            base_cmd += ['-p', str(port)]

        destination = f"{username}@{host}" if username else host
        cmd = list(base_cmd)

        if auth_method == 'SSH_KEY' and secret:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.key', encoding='utf-8') as tmp_key:
                tmp_key.write(secret)
                tmp_key_file = tmp_key.name
            os.chmod(tmp_key_file, 0o600)
            cmd += ['-i', tmp_key_file]
        elif auth_method == 'PASSWORD' and secret:
            cmd = ['sshpass', '-p', secret] + cmd

        if interpreter == 'python':
            cmd += [destination, 'python3', '-']
        else:
            cmd += [destination, 'bash', '-s']

        try:
            return subprocess.run(cmd, input=script_content.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        finally:
            if tmp_key_file and os.path.exists(tmp_key_file):
                try:
                    os.remove(tmp_key_file)
                except OSError:
                    pass

    @staticmethod
    def kill_job(eid):
        job = WorkflowExecution.objects.get(id=eid)
        execution_manager.terminate_node_process(eid)
        job.status = "TERMINATED"
        job.ended_at = timezone.now()
        job.save()
        ExecutionHubService._archive_execution(job)
        return job

    @staticmethod
    def pause_job(eid):
        job = WorkflowExecution.objects.get(id=eid)
        execution_manager.pause_workflow_chain(job.chain_id)
        job.status = "PAUSED"
        job.save()
        return job

    @staticmethod
    def resume_job(eid):
        job = WorkflowExecution.objects.get(id=eid)
        execution_manager.resume_workflow_chain(job.chain_id)
        job.status = "RUNNING"
        job.save()
        return job

    @staticmethod
    def force_ok(eid):
        job = WorkflowExecution.objects.get(id=eid)
        execution_manager.bypass_node_failure(eid)
        job.status = "COMPLETED"
        job.ended_at = timezone.now()
        job.save()
        ExecutionHubService._archive_execution(job)
        return job

    # --- Add more methods here for other 15 logic blocks... ---
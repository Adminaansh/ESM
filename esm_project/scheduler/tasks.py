import logging
import threading
import time
from datetime import timedelta
from django.db import transaction, DatabaseError, close_old_connections
from django.utils import timezone
from .models import AutomatedSchedule, TriggerIncidentLog
from execution_hub.services import ExecutionHubService

logger = logging.getLogger(__name__)
_scheduler_thread = None
_scheduler_stop_event = None


def evaluate_schedules():
    close_old_connections()
    now = timezone.now()
    active_rules = AutomatedSchedule.objects.filter(is_enabled=True)
    triggered_jobs = []

    for rule in active_rules:
        should_fire = False

        if rule.trigger_type == 'INTERVAL' and rule.interval_seconds:
            if not rule.last_fired_at:
                should_fire = True
            elif now >= rule.last_fired_at + timedelta(seconds=rule.interval_seconds):
                should_fire = True

        elif rule.trigger_type == 'CHRONOLOGICAL' and rule.fixed_time:
            current_time = now.time()
            already_run_today = rule.last_fired_at and rule.last_fired_at.date() == now.date()

            if current_time >= rule.fixed_time and not already_run_today:
                threshold_time = (timezone.datetime.combine(now.date(), rule.fixed_time) + timedelta(minutes=5)).time()
                if current_time <= threshold_time:
                    should_fire = True

        if should_fire:
            try:
                spawned = ExecutionHubService.run_job(rule.chain_id, source="scheduler")
                mock_spawned_execution_id = spawned.id
                was_successful = True
                error_details = None
            except Exception as exc:
                mock_spawned_execution_id = None
                was_successful = False
                error_details = str(exc)
                logger.exception(f"Failed to spawn scheduled job for rule {rule.id}: {exc}")

            # Update rule firing metadata regardless of success to avoid constant re-triggering.
            # Use a direct update to avoid the model save() normalization path and reduce SQLite lock contention.
            update_data = {
                'last_fired_at': now,
            }
            if rule.trigger_type == 'INTERVAL' and rule.interval_seconds:
                update_data['next_expected_fire'] = now + timedelta(seconds=rule.interval_seconds)

            attempt = 0
            while attempt < 5:
                try:
                    close_old_connections()
                    AutomatedSchedule.objects.filter(pk=rule.pk).update(**update_data)
                    break
                except DatabaseError as exc:
                    if attempt >= 4 or 'locked' not in str(exc).lower():
                        logger.exception('Failed to persist schedule update for rule %s after retry', rule.id)
                        raise
                    attempt += 1
                    logger.warning('SQLite locked while updating schedule %s, retrying...', rule.id)
                    time.sleep(0.2 * attempt)

            try:
                TriggerIncidentLog.objects.create(
                    schedule=rule,
                    spawned_execution_id=mock_spawned_execution_id,
                    was_successful=was_successful,
                    error_details=error_details
                )
            except DatabaseError as exc:
                logger.exception('Failed to create schedule incident for rule %s: %s', rule.id, exc)

            triggered_jobs.append({
                "schedule_id": str(rule.id),
                "chain_id": str(rule.chain_id),
                "triggered_execution_id": str(mock_spawned_execution_id) if mock_spawned_execution_id else None,
                "was_successful": was_successful
            })

    return {
        "status": "pulse_processed",
        "timestamp": now.isoformat(),
        "total_evaluated_schedules": active_rules.count(),
        "jobs_triggered_count": len(triggered_jobs),
        "dispatched_executions": triggered_jobs
    }


def _scheduler_loop(interval_seconds=30):
    global _scheduler_stop_event
    _scheduler_stop_event = threading.Event()
    while not _scheduler_stop_event.is_set():
        try:
            evaluate_schedules()
        except Exception as exc:
            logger.exception('Scheduler loop error: %s', exc)
        _scheduler_stop_event.wait(interval_seconds)


def start_scheduler_thread(interval_seconds=30):
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return

    _scheduler_thread = threading.Thread(target=_scheduler_loop, kwargs={'interval_seconds': interval_seconds}, daemon=True, name='SchedulerEvaluator')
    _scheduler_thread.start()


def stop_scheduler_thread():
    global _scheduler_stop_event
    if _scheduler_stop_event is not None:
        _scheduler_stop_event.set()

import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from monitoring.models import WorkflowExecution
from engine.models import Chain


class MonitoringWebSocket(AsyncWebsocketConsumer):
    async def connect(self):
        self.state = 'ALL'
        self.search = ''
        self.last_payload = None
        self.update_task = None
        await self.accept()
        self.update_task = asyncio.create_task(self.update_loop())

    async def disconnect(self, close_code):
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

    async def receive(self, text_data):
        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = message.get('action')
        if action == 'subscribe':
            self.state = message.get('state', 'ALL') or 'ALL'
            self.search = message.get('search', '') or ''
            await self.send_updates(force=True)

    async def update_loop(self):
        while True:
            try:
                await asyncio.sleep(3)
                await self.send_updates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Update loop error: {e}")
                await asyncio.sleep(3)

    async def send_updates(self, force=False):
        data = await self.fetch_executions(self.state, self.search)
        payload = json.dumps({
            'type': 'monitoring_update',
            'executions': data,
        })
        if force or payload != self.last_payload:
            await self.send(text_data=payload)
            self.last_payload = payload

    @sync_to_async
    def fetch_executions(self, state_filter, search_filter):
        queryset = WorkflowExecution.objects.all().order_by('-started_at')
        if state_filter and state_filter != 'ALL':
            if state_filter == 'RUNNING_FAILED':
                queryset = queryset.filter(status__in=['RUNNING', 'FAILED'])
            else:
                queryset = queryset.filter(status=state_filter)

        if search_filter:
            queryset = queryset.filter(triggered_by__icontains=search_filter) | queryset.filter(id__icontains=search_filter)

        data_list = []
        for exe in queryset[:250]:
            chain_name = None
            try:
                chain = Chain.objects.filter(chain_code=int(exe.chain_id)).first() if str(exe.chain_id).isdigit() else None
                chain_name = chain.name if chain else None
            except Exception:
                chain_name = None

            started_at = exe.started_at
            ended_at = exe.ended_at
            elapsed = timezone.now() - started_at if not ended_at else ended_at - started_at
            elapsed_minutes = round(elapsed.total_seconds() / 60, 1)

            data_list.append({
                'process_no': exe.process_no,
                'execution_id': str(exe.id),
                'chain_id': str(exe.chain_id),
                'chain_name': chain_name,
                'task_name': chain_name or exe.triggered_by,
                'source': exe.triggered_by,
                'state': exe.status,
                'started_at': started_at.isoformat(),
                'ended_at': ended_at.isoformat() if ended_at else None,
                'elapsed_minutes': elapsed_minutes,
            })

        return data_list

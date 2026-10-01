from rest_framework import serializers
from .models import AutomatedSchedule, TriggerIncidentLog
from engine.models import Chain
from uuid import UUID


class TriggerIncidentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerIncidentLog
        fields = ['id', 'spawned_execution_id', 'was_successful', 'error_details', 'evaluated_at']


class AutomatedScheduleSerializer(serializers.ModelSerializer):
    incidents = TriggerIncidentLogSerializer(many=True, read_only=True)

    class Meta:
        model = AutomatedSchedule
        fields = [
            'id', 'chain_id', 'name', 'trigger_type', 'interval_seconds', 'fixed_time',
            'is_enabled', 'last_fired_at', 'next_expected_fire', 'created_at', 'incidents'
        ]

    def validate_chain_id(self, value):
        if value is None or str(value).strip() == '':
            raise serializers.ValidationError('chain_id is required')

        chain_obj = None
        if str(value).isdigit():
            chain_obj = Chain.objects.filter(chain_code=int(value)).first()
        else:
            try:
                guid = UUID(str(value))
                chain_obj = Chain.objects.filter(chain_guid=guid).first()
            except Exception:
                chain_obj = None

        if not chain_obj:
            raise serializers.ValidationError('Unable to resolve chain reference. Provide a valid chain_code or chain_guid.')

        return str(chain_obj.chain_code)

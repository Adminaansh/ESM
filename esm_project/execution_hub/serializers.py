from rest_framework import serializers

class ExecutionActionSerializer(serializers.Serializer):
    execution_id = serializers.UUIDField()

class ExecutionBulkSerializer(serializers.Serializer):
    execution_ids = serializers.ListField(child=serializers.UUIDField())

class ExecutionConfigSerializer(serializers.Serializer):
    priority = serializers.IntegerField(required=False)
    ttl_seconds = serializers.IntegerField(required=False)
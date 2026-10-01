from django.db.models import Max
from rest_framework import serializers
from .models import JobObject, ScriptRevision, PromptSet, Platform

class PromptSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptSet
        fields = ['id', 'variable_name', 'label', 'field_type', 'default_value']

class ScriptRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScriptRevision
        fields = ['version', 'content', 'pre_process', 'post_process', 'change_summary', 'created_at']


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = [
            'id', 'code', 'label', 'description', 'platform_type',
            'host', 'port', 'username', 'auth_method', 'secret_reference',
            'api_url', 'api_method', 'api_headers', 'api_body_template',
            'api_callback_path', 'api_callback_secret', 'api_timeout_seconds',
            'is_active'
        ]


class JobObjectSerializer(serializers.ModelSerializer):
    revisions = ScriptRevisionSerializer(many=True, read_only=True)
    prompts = PromptSetSerializer(many=True, read_only=True)
    platform_obj = serializers.PrimaryKeyRelatedField(queryset=Platform.objects.filter(is_active=True), allow_null=True, required=False)
    platform_obj_detail = PlatformSerializer(source='platform_obj', read_only=True)

    # Write-only field for the initial creation or revision update.
    script_content = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = JobObject
        fields = [
            'id', 'name', 'title', 'platform', 'platform_obj', 'platform_obj_detail', 'script_language',
            'remote_host', 'remote_port', 'remote_username', 'remote_auth_method', 'remote_secret_reference',
            'is_active', 'active_revision', 'tags', 'revisions', 'prompts', 'script_content'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        active_revision = instance.revisions.filter(version=instance.active_revision).first()
        data['script_content'] = active_revision.content if active_revision else ''

        if instance.platform_obj:
            data['platform'] = instance.platform_obj.code
        return data

    def create(self, validated_data):
        script_content = validated_data.pop('script_content', '')
        platform_obj = validated_data.pop('platform_obj', None)
        if platform_obj is not None:
            validated_data['platform'] = platform_obj.code

        user = self.context['request'].user
        job = JobObject.objects.create(**validated_data, owner=user, platform_obj=platform_obj)

        # Initialize Version 1
        ScriptRevision.objects.create(
            job_object=job,
            version=1,
            content=script_content,
            created_by=user
        )
        return job

    def update(self, instance, validated_data):
        script_content = validated_data.pop('script_content', None)
        platform_obj = validated_data.pop('platform_obj', None)

        if platform_obj is not None:
            validated_data['platform'] = platform_obj.code
            instance.platform_obj = platform_obj
        elif 'platform' in validated_data and validated_data['platform']:
            instance.platform_obj = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if script_content is not None and script_content != '':
            latest_version = instance.revisions.aggregate(Max('version'))['version__max'] or 0
            ScriptRevision.objects.create(
                job_object=instance,
                version=latest_version + 1,
                content=script_content,
                created_by=self.context['request'].user
            )
            instance.active_revision = latest_version + 1

        instance.save()
        return instance         
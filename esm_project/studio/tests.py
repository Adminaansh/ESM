from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import JobObject, ScriptRevision
from .serializers import JobObjectSerializer

User = get_user_model()


class JobObjectSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.factory = APIRequestFactory()
        self.request = self.factory.post('/api/v1/studio/objects/')
        self.request.user = self.user

    def test_create_job_with_script_content_and_serializes_script(self):
        payload = {
            'name': 'TEST_JOB_WITH_SCRIPT',
            'title': 'Test Job',
            'platform': 'UNIX',
            'is_active': True,
            'tags': ['test'],
            'script_content': 'print("hello world")'
        }

        serializer = JobObjectSerializer(data=payload, context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        job = serializer.save()

        self.assertEqual(job.active_revision, 1)
        self.assertEqual(job.revisions.count(), 1)
        self.assertEqual(job.revisions.first().content, payload['script_content'])

        rendered = JobObjectSerializer(job).data
        self.assertEqual(rendered['script_content'], payload['script_content'])

    def test_create_job_without_script_content_does_not_fail(self):
        payload = {
            'name': 'TEST_JOB_NO_SCRIPT',
            'title': 'No Script Job',
            'platform': 'UNIX',
            'is_active': True,
            'tags': []
        }

        serializer = JobObjectSerializer(data=payload, context={'request': self.request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        job = serializer.save()

        self.assertEqual(job.active_revision, 1)
        self.assertEqual(job.revisions.count(), 1)
        self.assertEqual(job.revisions.first().content, '')
        self.assertEqual(JobObjectSerializer(job).data['script_content'], '')

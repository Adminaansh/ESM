import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowExecutionStep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('node_id', models.UUIDField(blank=True, null=True)),
                ('job_name', models.CharField(max_length=255)),
                ('sequence_index', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('QUEUED', 'Queued'), ('RUNNING', 'Running'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('TERMINATED', 'Terminated')], default='QUEUED', max_length=20)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='monitoring.workflowexecution')),
            ],
            options={
                'ordering': ['sequence_index'],
            },
        ),
    ]

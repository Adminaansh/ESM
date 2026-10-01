import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0002_workflowexecutionstep'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflowexecution',
            name='chain_id',
            field=models.CharField(max_length=20),
        ),
        migrations.CreateModel(
            name='WorkflowExecutionHistory',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, serialize=False, editable=False)),
                ('original_execution_id', models.UUIDField(blank=True, null=True)),
                ('process_no', models.PositiveIntegerField()),
                ('chain_id', models.CharField(max_length=20)),
                ('chain_name', models.CharField(blank=True, max_length=255, null=True)),
                ('task_name', models.CharField(blank=True, max_length=255, null=True)),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(max_length=20)),
                ('started_at', models.DateTimeField()),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('archived_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-archived_at'],
            },
        ),
    ]

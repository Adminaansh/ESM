from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0003_add_execution_history'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflowexecution',
            name='status',
            field=models.CharField(choices=[('QUEUED', 'Queued'), ('RUNNING', 'Running'), ('HOLD', 'Hold'), ('PAUSED', 'Paused'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('TERMINATED', 'Terminated')], default='QUEUED', max_length=20),
        ),
    ]

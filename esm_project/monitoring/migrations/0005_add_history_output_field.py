from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0004_alter_workflowexecution_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflowexecutionhistory',
            name='compiled_console_output',
            field=models.TextField(blank=True, default=''),
        ),
    ]

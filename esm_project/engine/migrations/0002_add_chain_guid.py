from django.db import migrations, models
import uuid

def generate_unique_chain_guids(apps, schema_editor):
    Chain = apps.get_model('engine', 'Chain')
    for chain in Chain.objects.filter(chain_guid__isnull=True):
        chain.chain_guid = uuid.uuid4()
        chain.save(update_fields=['chain_guid'])

class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chain',
            name='chain_guid',
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(generate_unique_chain_guids, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='chain',
            name='chain_guid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

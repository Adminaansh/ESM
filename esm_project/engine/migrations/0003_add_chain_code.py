from django.db import migrations, models
import random


def generate_chain_codes(apps, schema_editor):
    Chain = apps.get_model('engine', 'Chain')
    for chain in Chain.objects.all():
        if not chain.chain_code:
            code = random.randint(100000, 999999)
            while Chain.objects.filter(chain_code=code).exists():
                code = random.randint(100000, 999999)
            chain.chain_code = code
            chain.save()

class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0002_add_chain_guid'),
    ]

    operations = [
        migrations.AddField(
            model_name='chain',
            name='chain_code',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.RunPython(generate_chain_codes, reverse_code=migrations.RunPython.noop),
    ]

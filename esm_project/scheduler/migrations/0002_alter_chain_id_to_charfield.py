from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='automatedschedule',
            name='chain_id',
            field=models.CharField(max_length=20),
        ),
    ]

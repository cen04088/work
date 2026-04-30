# Generated manually for public data sync state.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PublicDataSyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=80, unique=True)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('last_status', models.CharField(blank=True, max_length=20)),
                ('last_message', models.TextField(blank=True)),
            ],
        ),
    ]

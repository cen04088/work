from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_employmentsupportcenter'),
    ]

    operations = [
        migrations.AddField(
            model_name='employmentsupportcenter',
            name='operating_hours',
            field=models.CharField(blank=True, help_text='운영시간', max_length=50),
        ),
        migrations.AddField(
            model_name='employmentsupportcenter',
            name='operator',
            field=models.CharField(blank=True, help_text='운영기관', max_length=100),
        ),
        migrations.AddField(
            model_name='employmentsupportcenter',
            name='source_updated_at',
            field=models.CharField(blank=True, help_text='데이터 수정일', max_length=20),
        ),
    ]

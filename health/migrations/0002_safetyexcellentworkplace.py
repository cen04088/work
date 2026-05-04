from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("health", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SafetyExcellentWorkplace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("post_number", models.CharField(blank=True, max_length=30)),
                ("labor_office", models.CharField(blank=True, max_length=80)),
                ("workplace_name", models.CharField(max_length=200)),
                ("construction_site_name", models.CharField(blank=True, max_length=200)),
                ("recognized_date", models.CharField(blank=True, max_length=30)),
            ],
            options={
                "ordering": ["-recognized_date", "workplace_name"],
            },
        ),
        migrations.AddIndex(
            model_name="safetyexcellentworkplace",
            index=models.Index(fields=["workplace_name"], name="health_safe_workpla_10b804_idx"),
        ),
        migrations.AddIndex(
            model_name="safetyexcellentworkplace",
            index=models.Index(fields=["construction_site_name"], name="health_safe_constru_0c2104_idx"),
        ),
        migrations.AddIndex(
            model_name="safetyexcellentworkplace",
            index=models.Index(fields=["labor_office"], name="health_safe_labor_o_5ae908_idx"),
        ),
    ]

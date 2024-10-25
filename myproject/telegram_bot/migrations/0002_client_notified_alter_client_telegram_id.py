# Generated by Django 5.1.2 on 2024-10-24 12:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='notified',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='client',
            name='telegram_id',
            field=models.CharField(max_length=50, unique=True),
        ),
    ]

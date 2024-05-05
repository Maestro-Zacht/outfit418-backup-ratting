# Generated by Django 4.2.11 on 2024-05-05 13:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('corptools', '0102_corporationaudit_last_change_contracts_and_more'),
        ('outfit418_backup_ratting', '0002_general'),
    ]

    operations = [
        migrations.CreateModel(
            name='CharacterAuditLoginData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('last_update', models.DateTimeField(blank=True, null=True)),
                ('characteraudit', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='corptools.characteraudit')),
            ],
        ),
    ]

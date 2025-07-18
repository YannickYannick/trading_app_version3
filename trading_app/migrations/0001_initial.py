# Generated by Django 5.2.4 on 2025-07-14 13:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Asset",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "symbol",
                    models.CharField(default="xxxx", max_length=20, unique=True),
                ),
                ("name", models.CharField(default="xxxx", max_length=100)),
                ("type", models.CharField(default="xxxx", max_length=20)),
                ("platform", models.CharField(default="xxxx", max_length=20)),
                ("last_price", models.FloatField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("sector", models.CharField(default="xxxx", max_length=100)),
                ("industry", models.CharField(default="xxxx", max_length=100)),
                ("market_cap", models.FloatField(default=0)),
                ("price_history", models.TextField(default="xxxx")),
                ("data_source", models.TextField(default="yahoo")),
                ("id_from_platform", models.CharField(default="xxxx", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Strategy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Position",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "size",
                    models.DecimalField(decimal_places=2, default=0, max_digits=15),
                ),
                (
                    "entry_price",
                    models.DecimalField(decimal_places=5, default=0, max_digits=15),
                ),
                (
                    "current_price",
                    models.DecimalField(decimal_places=5, default=0, max_digits=15),
                ),
                ("side", models.CharField(max_length=4)),
                ("status", models.CharField(max_length=10)),
                (
                    "pnl",
                    models.DecimalField(decimal_places=2, default=0, max_digits=15),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="trading_app.asset",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "strategy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="trading_app.strategy",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Trade",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("size", models.DecimalField(decimal_places=2, max_digits=15)),
                ("price", models.DecimalField(decimal_places=5, max_digits=15)),
                ("side", models.CharField(max_length=4)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("platform", models.CharField(max_length=20)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="trading_app.asset",
                    ),
                ),
                (
                    "strategy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="trading_app.strategy",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]

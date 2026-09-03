# SESSION_234 — TASK_front-door Part 3: DealerOnboardingProfile gets
# store-level payment defaults so the est-payment line on the assistant
# and showroom cards can resolve without a customer-supplied down /
# term. All three fields nullable so historical rows keep the
# payment_engine module defaults; a Copper Canyon-style seed sets
# APR 19.00 / term 36 / down 20% (see TASK_front-door.md).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dealer_ai", "0060_de_ford_vehicle_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="default_apr",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, null=True, blank=True
            ),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="default_term_months",
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="dealeronboardingprofile",
            name="default_down_payment_pct",
            field=models.DecimalField(
                decimal_places=2, max_digits=5, null=True, blank=True
            ),
        ),
    ]

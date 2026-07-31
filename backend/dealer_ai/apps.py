from django.apps import AppConfig


class DealerAiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dealer_ai"
    verbose_name = "Dealer AI"

    def ready(self) -> None:
        # Milestone 1 · Increment 3 — wire the write-path tenancy
        # fallback. Any save() on the six tenant carriers without an
        # explicit dealership= gets the default row attached via the
        # pre_save signal registered here.
        from .services.tenancy import register_default_dealership_autofill

        register_default_dealership_autofill()

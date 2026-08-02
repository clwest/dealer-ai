"""Milestone 12 · Increment 5 (SESSION_125) — collection-language scrub tests.

Locks the FDCPA-adjacent scrub layer added to
:func:`dealer_ai.services.llm_safety.apply_post_llm_scrubs` under
``kind="collection_contact"``.

Three pattern categories per §1.5:

1. Deficiency threats — credit-bureau leverage, lawsuit threats,
   wage garnishment, jail-time threats.
2. Harassment-adjacent language — contacting employer / neighbors /
   family, repeated-contact pressure.
3. False-representation claims — impersonating attorneys, police,
   court officials, credit bureaus.

Scrub REWRITES the text (log-and-replace) — matches the M2
partial-scrub pattern per §0.a M12.5 decision 5.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from dealer_ai.services.llm_safety import apply_post_llm_scrubs


class CollectionScrubKindGatingTests(SimpleTestCase):
    def test_non_collection_kind_leaves_language_untouched(self) -> None:
        text = (
            "This is your attorney. We will sue you and garnish your wages "
            "if you don't pay by Friday."
        )
        # Under kind="chat" the collection scrub should NOT fire — but the
        # rate-language / internal-directive scrubs might still activate.
        # Assert the collection scrub is not in the fired list.
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertNotIn("collection_language", scrubs)

    def test_collection_kind_activates_scrub(self) -> None:
        text = "This is your attorney. Pay now or face consequences."
        _, scrubs, _ = apply_post_llm_scrubs(
            text, kind="collection_contact"
        )
        self.assertIn("collection_language", scrubs)


class CollectionScrubDeficiencyThreatTests(SimpleTestCase):
    KIND = "collection_contact"

    def test_credit_bureau_leverage_neutralized(self) -> None:
        text = "We will report you to the credit bureau if you don't pay."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("report you to", cleaned.lower())
        self.assertIn("may report late payments", cleaned.lower())

    def test_lawsuit_threat_softened(self) -> None:
        text = "We will sue you next week if the balance is not paid."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("we will sue you", cleaned.lower())
        self.assertIn("legal action", cleaned.lower())

    def test_wage_garnishment_threat_softened(self) -> None:
        text = "We will garnish your wages this month."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("we will garnish", cleaned.lower())
        self.assertIn("court order", cleaned.lower())

    def test_jail_threat_removed(self) -> None:
        text = "You could go to jail if you keep missing payments."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("jail", cleaned.lower())

    def test_arrest_threat_removed(self) -> None:
        text = "We will have you arrested if the check bounces."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("arrested", cleaned.lower())


class CollectionScrubHarassmentTests(SimpleTestCase):
    KIND = "collection_contact"

    def test_employer_contact_threat_removed(self) -> None:
        text = "We will call your employer to collect this debt."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("employer", cleaned.lower())

    def test_workplace_contact_threat_removed(self) -> None:
        text = "We are going to call your workplace tomorrow."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("workplace", cleaned.lower())

    def test_neighbor_contact_threat_removed(self) -> None:
        text = "We will contact your neighbors about this account."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("neighbors", cleaned.lower())

    def test_repeated_contact_pressure_softened(self) -> None:
        text = "We will keep calling you until this is resolved."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("keep calling", cleaned.lower())
        self.assertIn("follow up", cleaned.lower())


class CollectionScrubFalseRepresentationTests(SimpleTestCase):
    KIND = "collection_contact"

    def test_attorney_impersonation_removed(self) -> None:
        text = "This is your attorney calling about the past-due balance."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("attorney", cleaned.lower())

    def test_police_impersonation_removed(self) -> None:
        text = "This is from the police department about your account."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("police", cleaned.lower())

    def test_court_impersonation_removed(self) -> None:
        text = "We are from the court and need immediate payment."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("court", cleaned.lower())

    def test_credit_bureau_impersonation_removed(self) -> None:
        text = "I am from the credit bureau and need to verify your account."
        cleaned, scrubs, _ = apply_post_llm_scrubs(text, kind=self.KIND)
        self.assertIn("collection_language", scrubs)
        self.assertNotIn("credit bureau", cleaned.lower())


class CollectionScrubCleanTextTests(SimpleTestCase):
    KIND = "collection_contact"

    def test_neutral_reminder_passes_through_unchanged(self) -> None:
        text = (
            "Hi Sam — just a reminder that your payment is due on the 15th. "
            "Please give us a call at 555-0100 to schedule."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(
            text, kind=self.KIND
        )
        # Neutral text should not activate the scrub layer.
        self.assertNotIn("collection_language", scrubs)
        self.assertIsNone(dropped)
        self.assertEqual(cleaned, text)

    def test_empty_input_returns_early(self) -> None:
        cleaned, scrubs, dropped = apply_post_llm_scrubs("", kind=self.KIND)
        self.assertEqual(cleaned, "")
        self.assertEqual(scrubs, [])
        self.assertIsNone(dropped)

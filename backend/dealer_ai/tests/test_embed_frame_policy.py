from django.test import TestCase, override_settings


class EmbedFramePolicyTests(TestCase):
    @override_settings(DEALER_AI_EMBED_ALLOWED_ORIGINS=["https://dealer.example"])
    def test_embed_path_gets_frame_ancestors_allowlist_and_no_xfo(self):
        res = self.client.get("/embed/assistant")

        self.assertNotIn("X-Frame-Options", res.headers)
        self.assertEqual(
            res.headers["Content-Security-Policy"],
            "frame-ancestors 'self' https://dealer.example",
        )

    def test_non_embed_paths_keep_default_x_frame_options(self):
        res = self.client.get("/api/dealer-ai/onboarding/profile/")

        self.assertEqual(res.headers["X-Frame-Options"], "DENY")
        self.assertNotIn("Content-Security-Policy", res.headers)

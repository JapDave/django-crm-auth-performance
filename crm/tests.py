from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .models import Contact, Deal
from .serializers import ContactSerializer, DealSerializer


@override_settings(SECURE_SSL_REDIRECT=False)
class CRMTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = get_user_model().objects.create_user("alice", password="test-password")
        cls.bob = get_user_model().objects.create_user("bob", password="test-password")
        cls.own = Contact.objects.create(owner=cls.alice, name="Own", email="own@example.com")
        cls.other = Contact.objects.create(owner=cls.bob, name="Other", email="other@example.com")
        cls.deal = Deal.objects.create(contact=cls.own, title="Pilot", value="500.00")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.alice)

    def test_anonymous_cannot_read(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/contacts/").status_code, 403)

    def test_list_is_owner_scoped(self):
        response = self.client.get("/api/contacts/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["deal_count"], 1)

    def test_other_owner_detail_hidden(self):
        self.assertEqual(self.client.patch(f"/api/contacts/{self.other.pk}/", {"name": "Changed"}).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/contacts/{self.other.pk}/").status_code, 404)

    def test_cannot_assign_deal_to_foreign_contact(self):
        response = self.client.post("/api/deals/", {"contact": self.other.pk, "title": "Bad", "value": "10.00"})
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f"/api/deals/{self.deal.pk}/", {"contact": self.other.pk})
        self.assertEqual(response.status_code, 400)

    def test_foreign_deal_hidden(self):
        deal = Deal.objects.create(contact=self.other, title="Private", value=10)
        self.assertEqual(self.client.get(f"/api/deals/{deal.pk}/").status_code, 404)

    def test_create_ignores_owner_override_and_normalizes_email(self):
        response = self.client.post("/api/contacts/", {"name": "New", "email": "NEW@EXAMPLE.COM", "owner": self.bob.pk})
        self.assertEqual(response.status_code, 201)
        created = Contact.objects.get(pk=response.data["id"])
        self.assertEqual(created.owner, self.alice)
        self.assertEqual(created.email, "new@example.com")

    def test_duplicate_email_rejected(self):
        response = self.client.post("/api/contacts/", {"name": "Duplicate", "email": "OWN@EXAMPLE.COM"})
        self.assertEqual(response.status_code, 400)

    def test_negative_deal_value_rejected(self):
        self.assertEqual(self.client.post("/api/deals/", {"contact": self.own.pk, "title": "Bad", "value": "-1"}).status_code, 400)

    def test_contact_with_deals_is_protected(self):
        self.assertEqual(self.client.delete(f"/api/contacts/{self.own.pk}/").status_code, 409)

    def test_partial_update_and_stage_filter(self):
        response = self.client.patch(f"/api/deals/{self.deal.pk}/", {"stage": "won"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/deals/?stage=won").data["count"], 1)
        self.assertEqual(self.client.get("/api/deals/?stage=lost").data["count"], 0)

    def test_deal_list_query_count_does_not_grow_with_records(self):
        for i in range(30):
            contact = Contact.objects.create(owner=self.alice, name=f"Contact {i}", email=f"c{i}@example.com")
            Deal.objects.create(contact=contact, title=f"Deal {i}", value=20)
        with self.assertNumQueries(2):
            response = self.client.get("/api/deals/")
            self.assertEqual(len(response.data["results"]), 25)

    def test_contact_list_query_budget(self):
        with self.assertNumQueries(2):
            self.assertEqual(self.client.get("/api/contacts/").status_code, 200)

    def test_google_signin_requires_post_and_account_linking_is_not_automatic(self):
        from django.conf import settings
        response = self.client.get("/accounts/google/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'method="post"')
        self.assertFalse(settings.SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT)

    def test_session_auth_enforces_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.alice)
        self.assertEqual(client.post("/api/contacts/", {"name": "CSRF", "email": "csrf@example.com"}).status_code, 403)

    def test_serialization_query_comparison(self):
        for i in range(10):
            Deal.objects.create(contact=self.own, title=f"Example {i}", value=1)
        with CaptureQueriesContext(connection) as naive:
            DealSerializer(Deal.objects.filter(contact__owner=self.alice), many=True).data
        with CaptureQueriesContext(connection) as optimized:
            DealSerializer(Deal.objects.filter(contact__owner=self.alice).select_related("contact"), many=True).data
        self.assertEqual(len(naive), 12)
        self.assertEqual(len(optimized), 1)

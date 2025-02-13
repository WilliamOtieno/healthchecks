# coding: utf-8

from datetime import timedelta as td
import json
from unittest.mock import patch

from django.utils.timezone import now
from hc.api.models import Channel, Check, Notification
from hc.test import BaseTestCase
from django.test.utils import override_settings


class NotifyPdTestCase(BaseTestCase):
    def _setup_data(self, value, status="down", email_verified=True):
        self.check = Check(project=self.project)
        self.check.status = status
        self.check.last_ping = now() - td(minutes=61)
        self.check.save()

        self.channel = Channel(project=self.project)
        self.channel.kind = "pd"
        self.channel.value = value
        self.channel.email_verified = email_verified
        self.channel.save()
        self.channel.checks.add(self.check)

    @patch("hc.api.transports.requests.request")
    def test_pd(self, mock_post):
        self._setup_data("123")
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "123")

    @patch("hc.api.transports.requests.request")
    def test_pd_complex(self, mock_post):
        self._setup_data(json.dumps({"service_key": "456"}))
        mock_post.return_value.status_code = 200

        self.channel.notify(self.check)
        assert Notification.objects.count() == 1

        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["event_type"], "trigger")
        self.assertEqual(payload["service_key"], "456")

    @override_settings(PD_ENABLED=False)
    def test_it_requires_pd_enabled(self):
        self._setup_data("123")
        self.channel.notify(self.check)

        n = Notification.objects.get()
        self.assertEqual(n.error, "PagerDuty notifications are not enabled.")

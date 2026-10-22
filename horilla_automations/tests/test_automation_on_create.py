"""On-create automations without filter rows must still fire."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from horilla_automations.signals import send_automated_mail


class AutomationOnCreateWithoutConditionsTests(SimpleTestCase):
    def test_empty_conditions_are_treated_as_always_applicable(self):
        automation = MagicMock()
        automation.trigger = "on_create"

        with patch("horilla_automations.signals.send_mail") as send_mail:
            send_automated_mail(
                request=MagicMock(),
                created=True,
                automation=automation,
                query_strings=[],
                instance=MagicMock(),
                previous_instance=None,
            )
            send_mail.assert_called_once()

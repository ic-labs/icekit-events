"""
Tests for ``eventkit`` app.
"""

# WebTest API docs: http://webtest.readthedocs.org/en/latest/api.html

from datetime import datetime, timedelta

from django.core.urlresolvers import reverse
from django_dynamic_fixture import G
from django_webtest import WebTest

from eventkit import forms, models, views
from eventkit.utils import time
from eventkit.tests import models as test_models


class Forms(WebTest):
    def test(self):
        pass


class Models(WebTest):
    def test_BaseModel(self):
        """
        Test that ``modified`` field is updated on save.
        """
        obj = G(test_models.BaseModel)
        modified = obj.modified
        obj.save()
        self.assertNotEqual(obj.modified, modified)

    def test_Event(self):
        """
        Test repeating events.
        """
        # Start with no events.
        self.assertEqual(models.Event.objects.count(), 0)

        # Create an event with a daily repeat expression.
        event = G(
            models.Event,
            repeat_expression='FREQ=DAILY;INTERVAL=1;COUNT=20')
        self.assertEqual(models.Event.objects.count(), 1)

        # Propagate to repeat events.
        event.propagate()
        self.assertEqual(event.get_repeat_events().count(), 19)

        # Update an event and decouple from repeat events.
        event2 = event.get_repeat_events()[15]
        event2.title = 'event 2'
        event2.repeat_expression = None
        event2.save()
        self.assertEqual(event.get_repeat_events().count(), 18)
        self.assertEqual(event2.get_repeat_events().count(), 0)

        # Update an event and propagate.
        event3 = event.get_repeat_events()[10]
        event3.title = 'event 3'
        event3.save(propagate=True)
        self.assertEqual(event.get_repeat_events().count(), 10)
        self.assertEqual(event3.get_repeat_events().count(), 19)  # Should be 9, not 19, because count rule is being reset.

        # Update an event's repeat expression and propagate.
        event4 = event.get_repeat_events()[5]
        event4.repeat_expression = 'FREQ=DAILY;INTERVAL=1;COUNT=3'
        event4.save(propagate=True)
        self.assertEqual(event.get_repeat_events().count(), 5)
        self.assertEqual(event3.get_repeat_events().count(), 19)  # Should be 9, not 19, because count rule is being reset.
        self.assertEqual(event4.get_repeat_events().count(), 2)


class Views(WebTest):
    def test_index(self):
        response = self.app.get(reverse('eventkit_index'))
        response.mustcontain('Hello World')


class Time(WebTest):
    def test_round_datetime(self):
        m = 60
        h = m * 60
        d = h * 24
        # Input, output, precision, rounding.
        data = (
            # Round nearest.
            ((1999, 12, 31, 0, 0, 29), (1999, 12, 31, 0, 0, 0), m, time.ROUND_NEAREST),
            ((1999, 12, 31, 0, 0, 30), (1999, 12, 31, 0, 1, 0), m, time.ROUND_NEAREST),
            # Round up and down.
            ((1999, 12, 31, 0, 0, 29), (1999, 12, 31, 0, 1, 0), m, time.ROUND_UP),
            ((1999, 12, 31, 0, 0, 30), (1999, 12, 31, 0, 0, 0), m, time.ROUND_DOWN),
            # Strip microseconds.
            ((1999, 12, 31, 0, 0, 30, 999), (1999, 12, 31, 0, 1, 0), m, time.ROUND_NEAREST),
            # Timedelta as precision.
            ((1999, 12, 31, 0, 0, 30), (1999, 12, 31, 0, 1, 0), timedelta(seconds=m), time.ROUND_NEAREST),
            # Precisions: 5, 10, 15 20, 30 minutes, 1, 12 hours, 1 day.
            ((1999, 12, 31, 0, 2, 30), (1999, 12, 31, 0, 5, 0), m * 5, time.ROUND_NEAREST),
            ((1999, 12, 31, 0, 5, 0), (1999, 12, 31, 0, 10, 0), m * 10, time.ROUND_NEAREST),
            ((1999, 12, 31, 0, 7, 30), (1999, 12, 31, 0, 15, 0), m * 15, time.ROUND_NEAREST),
            ((1999, 12, 31, 0, 10, 0), (1999, 12, 31, 0, 20, 0), m * 20, time.ROUND_NEAREST),
            ((1999, 12, 31, 0, 15, 0), (1999, 12, 31, 0, 30, 0), m * 30, time.ROUND_NEAREST),
            ((1999, 12, 31, 0, 30, 0), (1999, 12, 31, 1, 0, 0), h, time.ROUND_NEAREST),
            ((1999, 12, 31, 6, 0, 0), (1999, 12, 31, 12, 0, 0), h * 12, time.ROUND_NEAREST),
            ((1999, 12, 31, 12, 0, 0), (2000, 1, 1, 0, 0, 0), d, time.ROUND_NEAREST),
            # Weekday as precision. 3 Jan 2000 = Monday.
            ((1999, 12, 30, 12, 0, 0), (2000, 1, 3, 0, 0, 0), time.MON, time.ROUND_NEAREST),
            ((1999, 12, 31, 12, 0, 0), (2000, 1, 4, 0, 0, 0), time.TUE, time.ROUND_NEAREST),
            ((2000, 1, 1, 12, 0, 0), (2000, 1, 5, 0, 0, 0), time.WED, time.ROUND_NEAREST),
            ((2000, 1, 2, 12, 0, 0), (2000, 1, 6, 0, 0, 0), time.THU, time.ROUND_NEAREST),
            ((2000, 1, 3, 12, 0, 0), (2000, 1, 7, 0, 0, 0), time.FRI, time.ROUND_NEAREST),
            ((2000, 1, 4, 12, 0, 0), (2000, 1, 8, 0, 0, 0), time.SAT, time.ROUND_NEAREST),
            ((2000, 1, 5, 12, 0, 0), (2000, 1, 9, 0, 0, 0), time.SUN, time.ROUND_NEAREST),
        )
        for dt1, dt2, precision, rounding in data:
            self.assertEqual(
                time.round_datetime(datetime(*dt1), precision, rounding),
                datetime(*dt2))

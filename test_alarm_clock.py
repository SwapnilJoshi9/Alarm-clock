#!/usr/bin/env python3
"""Unit tests for Alarm_clock.py. Run with: python3 -m unittest test_alarm_clock.py"""

import datetime
import time
import unittest

import Alarm_clock as alarm_mod


class AlarmTriggerTests(unittest.TestCase):
    def setUp(self):
        self.clock = alarm_mod.AlarmClock()
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        alarm_mod.set_fake_now(None)

    def _assert_alarm_rings_at(self, hour: int, minute: int, label: str):
        alarm = self.clock.add_alarm(datetime.time(hour, minute), label=label)

        time.sleep(5)

        fake_now = datetime.datetime.combine(datetime.date.today(), datetime.time(hour, minute))
        alarm_mod.set_fake_now(fake_now)
        print(f"Current time: {fake_now.strftime('%I:%M %p')}")

        time.sleep(2)

        alarms = {a.id: a for a in self.clock.list_alarms()}
        self.assertEqual(alarms[alarm.id].status, "ringing")

        self.clock.delete_alarm(alarm.id)

    def test_alarm_at_5_25_pm(self):
        self._assert_alarm_rings_at(17, 25, label="5:25 PM alarm")

    def test_alarm_at_10_30_am(self):
        self._assert_alarm_rings_at(10, 30, label="10:30 AM alarm")

    def test_alarm_at_6_45_pm_repeats_daily_for_4_days(self):
        alarm = self.clock.add_alarm(datetime.time(18, 45), label="6:45 PM daily alarm", repeat_daily=True)

        time.sleep(5)

        base_date = datetime.date.today()
        for day_offset in range(4):
            fake_now = datetime.datetime.combine(
                base_date + datetime.timedelta(days=day_offset), datetime.time(18, 45)
            )
            alarm_mod.set_fake_now(fake_now)
            print(f"Current time: {fake_now.strftime('%m/%d %I:%M %p')}")

            time.sleep(2)

            alarms = {a.id: a for a in self.clock.list_alarms()}
            self.assertEqual(alarms[alarm.id].status, "ringing", f"day {day_offset + 1} of 4")

            # Cancel rearms a ringing daily alarm to "pending" so the next
            # simulated day can trigger it again.
            self.clock.cancel_alarm(alarm.id)
            alarms = {a.id: a for a in self.clock.list_alarms()}
            self.assertEqual(alarms[alarm.id].status, "pending", f"day {day_offset + 1} of 4")

        self.clock.delete_alarm(alarm.id)
        self.assertNotIn(alarm.id, {a.id for a in self.clock.list_alarms()})

    def test_alarm_at_8_30_am_snooze(self):
        alarm = self.clock.add_alarm(datetime.time(8, 30), label="8:30 AM alarm")

        time.sleep(5)

        fake_now = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 30))
        alarm_mod.set_fake_now(fake_now)
        print(f"Current time: {fake_now.strftime('%I:%M %p')}")

        time.sleep(2)

        alarms = {a.id: a for a in self.clock.list_alarms()}
        self.assertEqual(alarms[alarm.id].status, "ringing")

        snoozed = self.clock.snooze_alarm(alarm.id)
        self.assertIsNotNone(snoozed)
        self.assertEqual(snoozed.status, "snoozed")

        for elapsed in range(1, alarm_mod.SNOOZE_SECONDS + 2):
            time.sleep(1)
            alarms = {a.id: a for a in self.clock.list_alarms()}
            status = alarms[alarm.id].status
            print(f"{elapsed}s after snooze -> status: {status}")

            if elapsed < alarm_mod.SNOOZE_SECONDS:
                self.assertEqual(status, "snoozed", f"should still be snoozed at {elapsed}s")
            elif elapsed >= alarm_mod.SNOOZE_SECONDS + 1:
                self.assertEqual(status, "ringing", f"should be ringing again by {elapsed}s")

        self.clock.cancel_alarm(alarm.id)
        self.clock.delete_alarm(alarm.id)
        self.assertNotIn(alarm.id, {a.id for a in self.clock.list_alarms()})


if __name__ == "__main__":
    unittest.main()

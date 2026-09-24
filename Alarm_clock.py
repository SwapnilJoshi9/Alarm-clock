#!/usr/bin/env python3
"""Terminal-based alarm clock. Run with: python3 Alarm_clock.py"""

from __future__ import annotations

import datetime
import platform
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass

RING_TIMEOUT_SECONDS = 60
RING_INTERVAL_SECONDS = 2
SNOOZE_SECONDS = 5

STATUS_LABELS = {
    "pending": "⏰ pending",
    "ringing": "🔔 RINGING",
    "snoozed": "💤 snoozed",
    "done": "✅ done",
    "canceled": "🚫 canceled",
}


_fake_now: datetime.datetime | None = None


def get_now() -> datetime.datetime:
    """Current time used by the alarm checker. Real time by default;
    tests can override it with set_fake_now()."""
    return _fake_now if _fake_now is not None else datetime.datetime.now()


def set_fake_now(dt: datetime.datetime | None) -> None:
    """Override get_now() for testing. Pass None to go back to real time."""
    global _fake_now
    _fake_now = dt


def play_bell() -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return
        if system == "Linux":
            for cmd in (
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["aplay", "/usr/share/sounds/alsa/Front_Center.wav"],
            ):
                if shutil.which(cmd[0]):
                    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
        elif system == "Windows":
            import winsound
            winsound.MessageBeep()
            return
    except Exception:
        pass
    print("\a", end="", flush=True)


@dataclass
class Alarm:
    id: int
    time: datetime.time
    label: str = ""
    repeat_daily: bool = False
    status: str = "pending"
    last_triggered_date: datetime.date | None = None
    ring_started_at: float | None = None
    snooze_until: float | None = None
    created_seq: int = 0

    def display_name(self) -> str:
        return self.label or f"Alarm #{self.id}"


class AlarmClock:
    """Alarm ids are display-only: they're recomputed by _renumber() to always
    match the alarm's position when sorted by time, so id 1 is whichever alarm
    rings soonest. Alarms are stored internally by their immutable creation
    sequence number so lookups survive renumbering."""

    def __init__(self):
        self._alarms: dict[int, Alarm] = {}
        self._next_seq = 1
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def add_alarm(self, alarm_time: datetime.time, label: str = "", repeat_daily: bool = False) -> Alarm:
        with self._lock:
            seq = self._next_seq
            self._next_seq += 1
            alarm = Alarm(id=0, time=alarm_time, label=label, repeat_daily=repeat_daily, created_seq=seq)
            self._alarms[seq] = alarm
            self._renumber()
            return alarm

    def _find(self, alarm_id: int) -> Alarm | None:
        return next((a for a in self._alarms.values() if a.id == alarm_id), None)

    def delete_alarm(self, alarm_id: int) -> Alarm | None:
        with self._lock:
            alarm = self._find(alarm_id)
            if alarm is None:
                return None
            del self._alarms[alarm.created_seq]
            self._renumber()
            return alarm

    def _renumber(self) -> None:
        ordered = sorted(self._alarms.values(), key=lambda a: (a.time, a.created_seq))
        for new_id, a in enumerate(ordered, start=1):
            a.id = new_id

    def cancel_alarm(self, alarm_id: int) -> tuple[Alarm | None, str | None]:
        with self._lock:
            alarm = self._find(alarm_id)
            if alarm is None:
                return None, None
            if alarm.status == "pending":
                alarm.status = "canceled"
                return alarm, "disabled"
            if alarm.status in ("ringing", "snoozed"):
                self._rearm_or_finish(alarm)
                return alarm, "silenced"
            return alarm, "already_inactive"

    def snooze_alarm(self, alarm_id: int, snooze_seconds: int = SNOOZE_SECONDS) -> Alarm | None:
        with self._lock:
            alarm = self._find(alarm_id)
            if alarm is None or alarm.status != "ringing":
                return None
            alarm.status = "snoozed"
            alarm.ring_started_at = None
            alarm.snooze_until = time.monotonic() + snooze_seconds
            return alarm

    def list_alarms(self) -> list[Alarm]:
        with self._lock:
            return sorted(self._alarms.values(), key=lambda a: (a.time, a.created_seq))

    def _rearm_or_finish(self, alarm: Alarm) -> None:
        alarm.ring_started_at = None
        alarm.snooze_until = None
        alarm.status = "pending" if alarm.repeat_daily else "done"
        self._renumber()

    def _checker_loop(self) -> None:
        while not self._stop_event.is_set():
            now = get_now()
            with self._lock:
                for alarm in self._alarms.values():
                    if alarm.status == "snoozed" and time.monotonic() >= alarm.snooze_until:
                        alarm.status = "ringing"
                        alarm.ring_started_at = time.monotonic()
                        alarm.snooze_until = None
                        continue
                    if alarm.status != "pending":
                        continue
                    if (now.hour, now.minute) != (alarm.time.hour, alarm.time.minute):
                        continue
                    if alarm.last_triggered_date == now.date():
                        continue
                    alarm.status = "ringing"
                    alarm.last_triggered_date = now.date()
                    alarm.ring_started_at = time.monotonic()
            time.sleep(1)

    def _ring_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                ringing = [a for a in self._alarms.values() if a.status == "ringing"]
                for alarm in ringing:
                    if alarm.ring_started_at and time.monotonic() - alarm.ring_started_at >= RING_TIMEOUT_SECONDS:
                        self._rearm_or_finish(alarm)
                ringing = [a for a in self._alarms.values() if a.status == "ringing"]
            if ringing:
                names = ", ".join(a.display_name() for a in ringing)
                ids = ", ".join(str(a.id) for a in ringing)
                print(f"\n\a🔔 ALARM! {names} — type 'cancel {ids}' to silence, or 'snooze {ids}' to snooze.")
                play_bell()
            time.sleep(RING_INTERVAL_SECONDS)

    def start(self) -> None:
        threading.Thread(target=self._checker_loop, daemon=True).start()
        threading.Thread(target=self._ring_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop_event.set()


HELP_TEXT = f"""
Commands:
  list                     Show all alarms
  add                      Create a new alarm (interactive prompts)
  delete <id>              Permanently remove an alarm
  cancel <id>              Disable a pending alarm, or silence one that's ringing
  snooze <id>              Silence a ringing alarm and re-ring it in {SNOOZE_SECONDS}s
  help                     Show this help message
  exit / quit              Quit the alarm clock
"""


def prompt_time() -> datetime.time:
    while True:
        raw = input("Alarm time (HH:MM, 24h): ").strip()
        try:
            return datetime.datetime.strptime(raw, "%H:%M").time()
        except ValueError:
            print("Invalid format. Use HH:MM, e.g. 07:30")


def print_alarms(alarms: list[Alarm]) -> None:
    if not alarms:
        print("No alarms set.")
        return
    print(f"{'ID':<4}{'Time':<9}{'Repeat':<8}{'Status':<14}Label")
    for a in alarms:
        repeat = "daily" if a.repeat_daily else "once"
        print(f"{a.id:<4}{a.time.strftime('%H:%M'):<9}{repeat:<8}{STATUS_LABELS[a.status]:<14}{a.label}")


def main() -> None:
    clock = AlarmClock()
    clock.start()
    print("=== Terminal Alarm Clock ===")
    print("Type 'help' for commands.\n")

    while True:
        try:
            raw = input("alarm> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("exit", "quit"):
            break
        elif cmd == "help":
            print(HELP_TEXT)
        elif cmd == "list":
            print_alarms(clock.list_alarms())
        elif cmd == "add":
            alarm_time = prompt_time()
            label = input("Label (optional): ").strip()
            repeat = input("Repeat daily? (y/N): ").strip().lower() == "y"
            alarm = clock.add_alarm(alarm_time, label, repeat)
            print(f"Added alarm #{alarm.id} at {alarm_time.strftime('%H:%M')} ({'daily' if repeat else 'once'})")
        elif cmd == "delete":
            if len(parts) < 2 or not parts[1].isdigit():
                print("Usage: delete <id>")
                continue
            alarm = clock.delete_alarm(int(parts[1]))
            print(f"Deleted alarm #{alarm.id}." if alarm else "No such alarm.")
        elif cmd == "cancel":
            if len(parts) < 2 or not parts[1].isdigit():
                print("Usage: cancel <id>")
                continue
            alarm, outcome = clock.cancel_alarm(int(parts[1]))
            if alarm is None:
                print("No such alarm.")
            elif outcome == "disabled":
                print(f"Canceled alarm #{alarm.id}.")
            elif outcome == "silenced":
                print(f"Silenced alarm #{alarm.id}.")
            else:
                print(f"Alarm #{alarm.id} is already inactive.")
        elif cmd == "snooze":
            if len(parts) < 2 or not parts[1].isdigit():
                print("Usage: snooze <id>")
                continue
            alarm = clock.snooze_alarm(int(parts[1]))
            print(f"Snoozed alarm #{alarm.id} for {SNOOZE_SECONDS}s." if alarm
                  else "No such alarm, or it isn't currently ringing.")
        else:
            print(f"Unknown command: {cmd}. Type 'help'.")

    clock.stop()


if __name__ == "__main__":
    main()

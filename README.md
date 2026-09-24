# Terminal Alarm Clock

A simple command-line alarm clock written in pure Python (no external
packages, no database, no network). Set one or more alarms and it rings a
bell sound right in your terminal when they go off.

## Requirements

- Python 3.9 or newer
- No `pip install` needed — everything used is from the standard library

## Running it

```bash
python3 Alarm_clock.py
```

You'll land on an `alarm>` prompt. Type `help` any time to see the command
list. The app keeps running in your terminal, checking the clock every
second in the background, so leave the window open for your alarms to ring.

## Commands

| Command        | What it does                                              |
|----------------|-------------------------------------------------------------|
| `list`         | Show all alarms                                           |
| `add`          | Create a new alarm (asks for time, label, and daily repeat) |
| `delete <id>`  | Permanently remove an alarm                                |
| `cancel <id>`  | Turn off a pending alarm, or silence one that's ringing    |
| `snooze <id>`  | Silence a ringing alarm and have it ring again in 5 seconds |
| `help`         | Show the command list                                     |
| `exit` / `quit`| Quit the program                                           |

## Example session

```
alarm> add
Alarm time (HH:MM, 24h): 07:30
Label (optional): Wake up
Repeat daily? (y/N): y
Added alarm #1 at 07:30 (daily)

alarm> list
ID  Time     Repeat  Status        Label
1   07:30    daily   ⏰ pending     Wake up

# ... at 07:30 ...
🔔 ALARM! Wake up — type 'cancel 1' to silence, or 'snooze 1' to snooze.

alarm> snooze 1
Snoozed alarm #1 for 5s.

# 5 seconds later it rings again
🔔 ALARM! Wake up — type 'cancel 1' to silence, or 'snooze 1' to snooze.

alarm> cancel 1
Silenced alarm #1.
```

## How it behaves

- **Multiple alarms**: add as many as you like; they all ring independently.
- **IDs stay tidy**: an alarm's `id` always matches its position in the
  time-sorted list, so ids never have gaps — e.g. deleting alarm 1 out of 4
  makes the old alarms 2, 3, 4 become 1, 2, 3.
- **Statuses**:
  - ⏰ `pending` — waiting for its scheduled time
  - 🔔 `RINGING` — going off right now
  - 💤 `snoozed` — silenced for 5 seconds, about to ring again
  - ✅ `done` — a one-time alarm that already rang
  - 🚫 `canceled` — a pending alarm you turned off before it rang
- **Daily alarms**: after ringing and being canceled/timed out, they go back
  to `pending` and will ring again at the same time the next day. One-time
  alarms move to `done` instead.
- **Auto-silence**: if you don't cancel or snooze a ringing alarm, it stops
  ringing on its own after 60 seconds (daily alarms rearm for tomorrow).
- **Sound**: plays a system bell — `afplay` on macOS, `paplay`/`aplay` on
  Linux, `winsound` on Windows — falling back to the terminal bell (`\a`) if
  none of those are available.
- **No persistence on purpose**: alarms live only in memory for as long as
  the program runs, so there's no database or config file to manage — this
  is by design, not a bug.

## Running the tests

```bash
python3 -m unittest test_alarm_clock.py -v
```

`test_alarm_clock.py` covers alarms triggering at specific times, daily
repeats firing across multiple simulated days, and the snooze timing. Since
waiting for a real alarm time in a test would be impractical, the tests use
`Alarm_clock.set_fake_now(...)` to fake "now" for the alarm checker instead
of waiting for the real clock — `Alarm_clock.py` itself always uses the real
system time by default.

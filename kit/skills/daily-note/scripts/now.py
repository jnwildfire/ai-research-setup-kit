#!/usr/bin/env python3
"""Print the local time, and the daily note that an entry written now belongs to.

Every time stamp the agent writes into a note (a progress-log "(HH:MM)", a date-modified value) is
taken from this output, never estimated: a model has no clock, and a session that counted on from
its start time once stamped an afternoon's entries "04:20" to "05:40". The formats are fixed here
and do not follow the computer's regional settings, which on some systems print "23.51" for HH:mm.

The working day may end after midnight: with DAY_ENDS_AT = 6, an entry written between 00:00 and
05:59 belongs to the previous calendar date's note, so that one evening's session is not split
across two notes. Set it to 0 for a day that ends at midnight.

Usage:
    python -I now.py                            now
    python -I now.py --at "2026-11-06 05:59"    a moment, to test the boundary
    python -I now.py --vault <folder>           another vault than NOTES_ROOT

Standard library only; Python 3.8 or later. Part of the ai-research-setup-kit; Copyright (c) 2026
Johannes Wildfeuer, MIT licence (see LICENSE.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

# ------------------------------------------------------------------------------- configuration
NOTES_ROOT = "<notes vault, for example C:/Users/you/OneDrive - Your University/Vault>"
DAILY = "<daily notes folder>/{yyyy}-{mm}/{date}.md"   # where a day's note lives, inside the vault
TEMPLATE = "<template folder>/daily-note.md"           # named in the output when the note is missing
DAY_ENDS_AT = 6                                        # hour; 0 = midnight
# --------------------------------------------------------------------------- end of configuration

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def describe(now: dt.datetime, vault: str | None):
    working = (now - dt.timedelta(hours=DAY_ENDS_AT)).date() if DAY_ENDS_AT else now.date()
    rel = DAILY.format(yyyy=f"{working.year:04d}", mm=f"{working.month:02d}", date=working.isoformat())
    if vault and "<" not in vault and "<" not in rel:
        exists = "yes" if os.path.isfile(os.path.join(os.path.expanduser(vault), rel)) else f"no, create it from {TEMPLATE}"
    else:
        exists = "unknown (set NOTES_ROOT and DAILY at the top of the script)"
    rule = (f"before {DAY_ENDS_AT:02d}:00, so the previous calendar day" if working != now.date()
            else "same as the calendar date")
    return [
        f"now        {now.strftime('%Y-%m-%dT%H:%M:%S')}",
        f"stamp      {now.strftime('%H:%M')}",
        f"calendar   {now.date().isoformat()} {DAYS[now.weekday()]}",
        f"working    {working.isoformat()} {DAYS[working.weekday()]}  ({rule})",
        f"note       {rel}",
        f"exists     {exists}",
    ]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--at", help='a moment to evaluate instead of now, e.g. "2026-11-06 05:59"')
    ap.add_argument("--vault", help="the vault (default: NOTES_ROOT)")
    ap.add_argument("--self-test", action="store_true", help="check the day boundary and the formats")
    args = ap.parse_args(argv)
    if args.self_test:
        cases = [("2026-11-06 05:59", "2026-11-05"), ("2026-11-06 06:00", "2026-11-06"),
                 ("2026-12-01 00:30", "2026-11-30"), ("2027-01-01 03:00", "2026-12-31")]
        failed = 0
        for at, want in cases:
            out = describe(dt.datetime.fromisoformat(at), None)
            ok = out[3].split()[1] == want if DAY_ENDS_AT == 6 else True
            ok = ok and out[1].split()[1] == at[11:16]
            failed += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {at} -> working day {out[3].split()[1]}, stamp {out[1].split()[1]}")
        print(f"\n{len(cases) - failed} of {len(cases)} checks passed" + ("" if DAY_ENDS_AT == 6 else
              " (the day boundary was checked only for DAY_ENDS_AT = 6)") + ".")
        return 1 if failed else 0
    now = dt.datetime.fromisoformat(args.at) if args.at else dt.datetime.now()
    print("\n".join(describe(now, args.vault or NOTES_ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

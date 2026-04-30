import calendar
from datetime import date, timedelta
from django.db.models import Prefetch
from .models import DefaultTimetable, ActualTimetable, RedDay


# ─────────────────────────────────────────────
# 1. Month → weeks (only dates in that month)
# ─────────────────────────────────────────────

def get_monthly_weeks(year, month):
    """
    Returns a list of weeks for the given month.
    Each week is a list of date objects that belong to that month only.
    Weeks always start on Monday.

    Example for March 2025:
    [
        [date(2025,3,3), date(2025,3,4), ..., date(2025,3,7)],   # week 1 (Mon–Fri only)
        [date(2025,3,10), ..., date(2025,3,14)],                  # week 2
        ...
    ]
    """
    # First and last day of the month
    first_day = date(year, month, 1)
    last_day  = date(year, month, calendar.monthrange(year, month)[1])

    # Step back to the Monday of the first week
    start = first_day - timedelta(days=first_day.weekday())

    weeks = []
    current = start

    while current <= last_day:
        week = []
        for i in range(7):   # Monday to Sunday
            day = current + timedelta(days=i)
            if day.month == month:   # only include days in this month
                week.append(day)
        if week:
            weeks.append(week)
        current += timedelta(weeks=1)

    return weeks


def get_week_by_number(year, month, week_number):
    """
    Returns a single week (list of dates) by its 1-based index
    within the month. Returns None if week_number is out of range.
    """
    weeks = get_monthly_weeks(year, month)
    try:
        return weeks[week_number - 1]
    except IndexError:
        return None


def get_week_count(year, month):
    """How many weeks are in this month (for pagination bounds)."""
    return len(get_monthly_weeks(year, month))


def get_current_week_number(year, month):
    """
    Returns the week number (1-based) within the month
    that contains today. Falls back to 1 if today is outside the month.
    """
    today = date.today()
    weeks = get_monthly_weeks(year, month)
    for i, week in enumerate(weeks, start=1):
        if today in week:
            return i
    return 1


# ─────────────────────────────────────────────
# 2. Red day helpers
# ─────────────────────────────────────────────

def get_red_dates(year, month):
    """
    Returns a set of dates marked as red days in the given month.
    Cached as a set for O(1) lookup.
    """
    return set(
        RedDay.objects
              .filter(date__year=year, date__month=month)
              .values_list('date', flat=True)
    )


def is_red_day(check_date, red_dates=None):
    """
    Check if a date is a red day.
    Pass red_dates (set) to avoid repeated DB hits in a loop.
    """
    if red_dates is not None:
        return check_date in red_dates
    return RedDay.objects.filter(date=check_date).exists()


# ─────────────────────────────────────────────
# 3. Week schedule builder
# ─────────────────────────────────────────────

def get_week_schedule(teacher, week_dates):
    """
    For each date in week_dates, build the schedule for that teacher.
    - If an ActualTimetable entry exists for that date+slot → use it.
    - Otherwise fall back to DefaultTimetable for that day_of_week.
    - If the date is a red day → mark it, no schedule shown.

    Returns a list of day-dicts, one per date in week_dates:
    [
        {
            'date':     date(2025, 3, 10),
            'weekday':  'Monday',
            'is_red':   False,
            'red_reason': '',
            'slots': [
                {
                    'slot_number':   1,
                    'time_slot':     '08:00–09:30',
                    'subject':       'Mathematics',
                    'room':          '204',
                    'group':         'CS-101',
                    'status':        'filled',   # or 'pending' / 'confirmed' / 'default'
                    'comment':       '',
                    'dekan_note':    '',
                    'actual_id':     12,          # None if no actual entry
                    'default_id':    3,
                    'editable':      True,
                },
                ...
            ]
        },
        ...
    ]
    """
    if not week_dates:
        return []

    year  = week_dates[0].year
    month = week_dates[0].month

    # One query: all red days in this month
    red_dates = get_red_dates(year, month)

    # One query: all actual entries for this teacher in this week
    actual_entries = (
        ActualTimetable.objects
            .filter(teacher=teacher , date__in=week_dates)
            .select_related('default_entry')
    )
    # Index by (date, slot_number) for O(1) lookup
    actual_map = {
        (entry.date, entry.slot_number): entry
        for entry in actual_entries
    }

    # One query: all default slots for this teacher (all days of week)
    week_day_numbers = list({d.weekday() for d in week_dates})
    default_slots = (
        DefaultTimetable.objects
            .filter(teacher=teacher, day_of_week__in=week_day_numbers, is_active=True)
            .order_by('day_of_week', 'slot_number')
    )
    # Index by day_of_week → list of slots
    default_map = {}
    for slot in default_slots:
        default_map.setdefault(slot.day_of_week, []).append(slot)

    # Build the response
    day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    schedule  = []

    for day_date in week_dates:
        is_red = day_date in red_dates
        red_reason = ''
        if is_red:
            try:
                red_reason = RedDay.objects.get(date=day_date).reason
            except RedDay.DoesNotExist:
                pass

        day_entry = {
            'date':       day_date,
            'weekday':    day_names[day_date.weekday()],
            'is_red':     is_red,
            'red_reason': red_reason,
            'slots':      [],
        }

        if not is_red:
            defaults = default_map.get(day_date.weekday(), [])
            for default in defaults:
                actual = actual_map.get((day_date, default.slot_number))

                if actual:
                    day_entry['slots'].append({
                        'slot_number': actual.slot_number,
                        'time_slot':   actual.time_slot,
                        'subject':     actual.subject,
                        'room':        actual.room,
                        'group':       actual.group,
                        'status':      actual.status,
                        'comment':     actual.comment,
                        'dekan_note':  actual.dekan_note,
                        'actual_id':   actual.id,
                        'default_id':  default.id,
                        'editable':    actual.status != 'confirmed',
                    })
                else:
                    # No actual entry yet — show default as pending
                    day_entry['slots'].append({
                        'slot_number': default.slot_number,
                        'time_slot':   default.time_slot,
                        'subject':     default.subject,
                        'room':        default.room,
                        'group':       default.group,
                        'status':      'default',   # not yet filled
                        'comment':     '',
                        'dekan_note':  '',
                        'actual_id':   None,
                        'default_id':  default.id,
                        'editable':    True,
                    })

        schedule.append(day_entry)

    return schedule


# ─────────────────────────────────────────────
# 4. Report helpers
# ─────────────────────────────────────────────

def get_week_completion_stats(teacher, week_dates):
    """
    Returns a dict with fill statistics for a given week.
    Used to show progress before submitting a report.

    {
        'total':     10,
        'filled':    7,
        'confirmed': 2,
        'pending':   1,
        'percent':   70,
    }
    """
    red_dates    = get_red_dates(week_dates[0].year, week_dates[0].month)
    active_dates = [d for d in week_dates if d not in red_dates]

    default_count = (
        DefaultTimetable.objects
            .filter(
                teacher=teacher,
                day_of_week__in=[d.weekday() for d in active_dates],
                is_active=True
            )
            .count()
    )

    actuals = ActualTimetable.objects.filter(
        teacher=teacher,
        date__in=active_dates
    )

    filled    = actuals.filter(status='filled').count()
    confirmed = actuals.filter(status='confirmed').count()
    total     = default_count
    done      = filled + confirmed

    return {
        'total':     total,
        'filled':    filled,
        'confirmed': confirmed,
        'pending':   total - done,
        'percent':   round((done / total * 100) if total else 0),
    }


def get_month_summary(teacher, year, month):
    """
    Returns per-week stats for an entire month.
    Used on the teacher's month overview page.

    [
        {'week_number': 1, 'dates': [...], 'stats': {...}},
        {'week_number': 2, 'dates': [...], 'stats': {...}},
        ...
    ]
    """
    weeks   = get_monthly_weeks(year, month)
    summary = []
    for i, week_dates in enumerate(weeks, start=1):
        summary.append({
            'week_number': i,
            'dates':       week_dates,
            'stats':       get_week_completion_stats(teacher, week_dates),
        })
    return summary
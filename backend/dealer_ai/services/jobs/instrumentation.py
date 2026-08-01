"""Milestone 7 · Increment 1 (SESSION_088) — ``@instrumented_task``.

Shared decorator that wraps every Celery task with uniform:

1. **Structured log on start.** ``logging.INFO`` — task name + truncated
   args/kwargs repr + a fresh ``JobRunLog`` row created with
   ``status='started'``.
2. **Structured log on end.** ``logging.INFO`` on success,
   ``logging.ERROR`` on failure. Duration recorded in ms.
3. **``JobRunLog`` row write.** One row per invocation; the start row
   is updated in place on end (``update_fields=('status', 'ended_at',
   'duration_ms', 'error_message')``) so success / failure share a
   single audit row.
4. **Retry-on-transient-error policy.** Default: network / DB deadlock
   errors trigger a Celery ``retry`` with exponential backoff, max 3
   attempts. Programming errors (``ValueError``, ``TypeError``,
   ``AttributeError``, ``AssertionError``) raise immediately without
   retry so bugs surface fast per M4-M6 lesson 6 (no silent-swallow).
5. **Tenant-context extraction.** If the task receives a keyword
   argument named ``dealership_id``, its value is stamped onto the
   ``JobRunLog`` row so the M8 dashboards can filter by tenant. Absence
   → ``dealership_id`` on the row falls back to the default via the
   ``services.tenancy`` pre_save signal (per §5.e Option A discussion
   in ``MILESTONE_7_PLANNING.md``).

**Composition with Celery.** :func:`instrumented_task` wraps
:func:`celery.shared_task` — the returned object is a Celery task with
the wrapper applied to its ``run`` body. Callers register the task via
the wrapped module-level name; the Celery worker's autodiscovery finds
it via ``dealer_kit/celery.py::app.autodiscover_tasks()``.

**Test posture.** When ``CELERY_TASK_ALWAYS_EAGER=True``, task
invocations run synchronously in the calling thread and the decorator's
``JobRunLog`` writes commit to the test DB inside the caller's
transaction. Tests that assert on log rows use ``TestCase`` (which wraps
each test in a transaction that rolls back) and query
``JobRunLog.objects.all()`` after the task returns.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.7 + §5.e +
§7 M7.1.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

from celery import shared_task
from django.utils import timezone

# Transient errors that trigger Celery retry. Kept as a tuple so
# extension is a one-line diff — future ``services/**/tasks.py`` modules
# can add domain-specific transient errors by importing this tuple and
# calling ``shared_task(autoretry_for=INSTRUMENTED_TRANSIENT_ERRORS + (MyError,))``.
# Programming errors (``ValueError``, ``TypeError``, ``AttributeError``,
# ``AssertionError``) are deliberately absent — those signal bugs and
# should fail loud.
INSTRUMENTED_TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)

_LOGGER = logging.getLogger("dealer_ai.jobs.instrumentation")

# Maximum length of ``args_summary`` in ``JobRunLog``. Matches the model
# ``CharField(max_length=255)``; the decorator truncates *before* the DB
# rejects.
_ARGS_SUMMARY_MAX_LEN = 255


def instrumented_task(
    *,
    name: str,
    max_retries: int = 3,
    default_retry_delay: int = 30,
    autoretry_for: tuple[type[Exception], ...] = INSTRUMENTED_TRANSIENT_ERRORS,
    retry_backoff: bool = True,
    retry_backoff_max: int = 600,
    retry_jitter: bool = True,
    **shared_task_kwargs: Any,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator factory that produces an instrumented Celery task.

    Usage::

        from dealer_ai.services.jobs import instrumented_task

        @instrumented_task(name="services.floor_plan.tasks.accrue_daily_interest")
        def accrue_daily_interest(*, dealership_id: int) -> None:
            ...  # business logic

    Parameters
    ----------
    name : str
        The Celery task name. Should be the dotted path to the task
        (e.g. ``"services.floor_plan.tasks.accrue_daily_interest"``).
        This value is also written to ``JobRunLog.task_name`` for every
        invocation.
    max_retries : int
        Passed through to Celery. Default 3 (per §1.7 policy).
    default_retry_delay : int
        Seconds before the first retry. Default 30.
    autoretry_for : tuple[type[Exception], ...]
        Exception classes that trigger a Celery retry. Defaults to
        :data:`INSTRUMENTED_TRANSIENT_ERRORS`. Programming errors (see
        module docstring) are intentionally not in this set — they
        should fail loud.
    retry_backoff : bool
        Passed through to Celery. Default True (exponential backoff).
    retry_backoff_max : int
        Max backoff in seconds. Default 600 (10 minutes).
    retry_jitter : bool
        Passed through to Celery. Default True (avoids thundering herd
        on transient outage recovery).
    **shared_task_kwargs
        Any other kwargs are forwarded to :func:`celery.shared_task`
        (e.g. ``queue="high_priority"``).

    Returns
    -------
    Callable
        A decorator that transforms the wrapped function into an
        instrumented Celery task.
    """

    def decorator(func: Callable[..., Any]) -> Any:
        @wraps(func)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            from dealer_ai.models import (
                JOB_RUN_STATUS_FAILED,
                JOB_RUN_STATUS_STARTED,
                JOB_RUN_STATUS_SUCCEEDED,
                JobRunLog,
            )

            dealership_id = kwargs.get("dealership_id")
            args_summary = _summarize_args(args, kwargs)

            started_at = timezone.now()
            log_row = JobRunLog.objects.create(
                task_name=name,
                status=JOB_RUN_STATUS_STARTED,
                started_at=started_at,
                args_summary=args_summary,
                dealership_id=dealership_id,
            )
            _LOGGER.info(
                "job.start task=%s args_summary=%s dealership_id=%s",
                name,
                args_summary,
                dealership_id,
            )
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 — decorator has to catch everything
                ended_at = timezone.now()
                duration_ms = _ms_between(started_at, ended_at)
                # Truncate the exception's ``str()`` to fit in a
                # queryable summary; the full traceback goes to the
                # structured log stream via ``logger.exception``.
                error_summary = _truncate(repr(exc), 4000)
                log_row.status = JOB_RUN_STATUS_FAILED
                log_row.ended_at = ended_at
                log_row.duration_ms = duration_ms
                log_row.error_message = error_summary
                log_row.save(
                    update_fields=(
                        "status",
                        "ended_at",
                        "duration_ms",
                        "error_message",
                    )
                )
                _LOGGER.exception(
                    "job.failed task=%s duration_ms=%s dealership_id=%s",
                    name,
                    duration_ms,
                    dealership_id,
                )
                raise
            else:
                ended_at = timezone.now()
                duration_ms = _ms_between(started_at, ended_at)
                log_row.status = JOB_RUN_STATUS_SUCCEEDED
                log_row.ended_at = ended_at
                log_row.duration_ms = duration_ms
                log_row.save(
                    update_fields=("status", "ended_at", "duration_ms")
                )
                _LOGGER.info(
                    "job.succeeded task=%s duration_ms=%s dealership_id=%s",
                    name,
                    duration_ms,
                    dealership_id,
                )
                return result

        return shared_task(
            name=name,
            max_retries=max_retries,
            default_retry_delay=default_retry_delay,
            autoretry_for=autoretry_for,
            retry_backoff=retry_backoff,
            retry_backoff_max=retry_backoff_max,
            retry_jitter=retry_jitter,
            **shared_task_kwargs,
        )(_wrapped)

    return decorator


def _summarize_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Return a ``<= _ARGS_SUMMARY_MAX_LEN`` repr of the invocation args.

    Format: ``"args=<repr> kwargs=<repr>"`` truncated with an ellipsis.
    Every value goes through :func:`repr` so ORM instances become
    ``<Model pk=N>`` rather than their (potentially sensitive) attribute
    payload — the args summary is for audit pattern-matching, not
    forensic replay. Forensic replay uses the broker payload (still
    live until the task's result expiry).
    """
    return _truncate(f"args={args!r} kwargs={kwargs!r}", _ARGS_SUMMARY_MAX_LEN)


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    # Reserve 3 chars for the ellipsis so the returned string always
    # fits inside ``max_len``.
    return value[: max_len - 3] + "..."


def _ms_between(start, end) -> int:
    """Return a non-negative integer millisecond delta.

    Uses :func:`round` so a task that ran ``0.499ms`` records 0 and one
    that ran ``0.5ms`` records 1 — matches humans' rounding intuition
    when reading a dashboard. ``max(0, ...)`` guards against clock skew
    (highly unlikely with a single-process eager path, but defensive
    against a future multi-worker deploy where the start and end wall
    clocks could differ).
    """
    delta = (end - start).total_seconds() * 1000
    return max(0, round(delta))

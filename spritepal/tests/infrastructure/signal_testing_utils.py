"""
Signal Testing Utilities - Real Qt Signal Testing Patterns

This module provides utilities for testing Qt signals with real components,
including signal spying, async waiting, and cross-thread signal validation.

Key Features:
- SignalSpy for monitoring signal emissions
- Async signal waiting with timeout
- Signal sequence validation
- Cross-thread signal testing
- Signal data capture and validation
"""

import time
from collections import deque
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6.QtCore import (
    QEventLoop,
    QObject,
    QThread,
    QTimer,
    Signal,
    SignalInstance,
)

from .qt_real_testing import EventLoopHelper


@dataclass
class SignalEmission:
    """Record of a signal emission."""

    signal_name: str
    timestamp: float
    args: tuple[Any, ...]
    thread: QThread

    def __str__(self) -> str:
        """String representation of emission."""
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.signal_name}({args_str}) at {self.timestamp:.3f}"


class SignalSpy:
    """
    Spy for monitoring Qt signal emissions.

    Replaces MockSignal with real signal monitoring capabilities.
    """

    def __init__(self, signal: Signal | SignalInstance, signal_name: str = "signal"):
        """
        Initialize signal spy.

        Args:
            signal: Signal to monitor
            signal_name: Name for logging purposes
        """
        self.signal = signal
        self.signal_name = signal_name
        self.emissions: list[SignalEmission] = []
        self._connected = False
        self._start_time = time.time()

        # Auto-connect
        self.connect()

    def connect(self):
        """Connect to the signal."""
        if not self._connected:
            self.signal.connect(self._on_signal)
            self._connected = True

    def disconnect(self):
        """Disconnect from the signal."""
        if self._connected:
            try:
                self.signal.disconnect(self._on_signal)
            except TypeError:
                # Already disconnected
                pass
            self._connected = False

    def _on_signal(self, *args):
        """Handle signal emission."""
        emission = SignalEmission(
            signal_name=self.signal_name,
            timestamp=time.time() - self._start_time,
            args=args,
            thread=QThread.currentThread()
        )
        self.emissions.append(emission)

    def clear(self):
        """Clear recorded emissions."""
        self.emissions.clear()
        self._start_time = time.time()

    def wait(self, timeout_ms: int = 1000, count: int = 1) -> bool:
        """
        Wait for signal emissions.

        Args:
            timeout_ms: Maximum wait time in milliseconds
            count: Number of emissions to wait for

        Returns:
            True if required emissions received, False if timeout
        """
        return EventLoopHelper.wait_until(
            lambda: len(self.emissions) >= count,
            timeout_ms=timeout_ms
        )

    def assert_emitted(self, count: int | None = None, timeout_ms: int = 100):
        """
        Assert signal was emitted.

        Args:
            count: Expected emission count (None = at least once)
            timeout_ms: Time to wait for emissions
        """
        # Wait a bit for async emissions
        EventLoopHelper.process_events(timeout_ms)

        if count is None:
            assert len(self.emissions) > 0, f"Signal {self.signal_name} was not emitted"
        else:
            assert len(self.emissions) == count, (
                f"Signal {self.signal_name} emitted {len(self.emissions)} times, "
                f"expected {count}"
            )

    def assert_not_emitted(self, timeout_ms: int = 100):
        """
        Assert signal was not emitted.

        Args:
            timeout_ms: Time to wait to ensure no emissions
        """
        EventLoopHelper.process_events(timeout_ms)
        assert len(self.emissions) == 0, (
            f"Signal {self.signal_name} was emitted {len(self.emissions)} times"
        )

    def assert_emitted_with(self, *expected_args, timeout_ms: int = 100):
        """
        Assert signal was emitted with specific arguments.

        Args:
            *expected_args: Expected signal arguments
            timeout_ms: Time to wait for emission
        """
        self.wait(timeout_ms, 1)

        assert len(self.emissions) > 0, f"Signal {self.signal_name} was not emitted"

        # Check last emission
        last_emission = self.emissions[-1]
        assert last_emission.args == expected_args, (
            f"Signal {self.signal_name} emitted with {last_emission.args}, "
            f"expected {expected_args}"
        )

    def get_emission(self, index: int = -1) -> SignalEmission | None:
        """
        Get specific emission.

        Args:
            index: Emission index (negative for reverse indexing)

        Returns:
            SignalEmission or None if index out of range
        """
        try:
            return self.emissions[index]
        except IndexError:
            return None

    def get_args(self, index: int = -1) -> tuple[Any, ...] | None:
        """
        Get arguments from specific emission.

        Args:
            index: Emission index

        Returns:
            Emission arguments or None
        """
        emission = self.get_emission(index)
        return emission.args if emission else None

    def __enter__(self):
        """Context manager entry."""
        self.clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Don't disconnect as signal might be used elsewhere
        pass

    def __len__(self) -> int:
        """Get number of emissions."""
        return len(self.emissions)

    def __bool__(self) -> bool:
        """Check if any emissions recorded."""
        return bool(self.emissions)


class MultiSignalSpy:
    """Spy for monitoring multiple signals simultaneously."""

    def __init__(self):
        """Initialize multi-signal spy."""
        self.spies: dict[str, SignalSpy] = {}
        self.all_emissions: list[SignalEmission] = []

    def add_signal(self, signal: Signal | SignalInstance, name: str) -> SignalSpy:
        """
        Add a signal to monitor.

        Args:
            signal: Signal to monitor
            name: Signal name for identification

        Returns:
            SignalSpy instance
        """
        spy = SignalSpy(signal, name)
        self.spies[name] = spy

        # Override spy's _on_signal to also record in all_emissions
        original_on_signal = spy._on_signal

        def combined_on_signal(*args):
            original_on_signal(*args)
            if spy.emissions:
                self.all_emissions.append(spy.emissions[-1])

        spy._on_signal = combined_on_signal

        return spy

    def get_spy(self, name: str) -> SignalSpy | None:
        """Get spy for specific signal."""
        return self.spies.get(name)

    def clear(self):
        """Clear all recorded emissions."""
        for spy in self.spies.values():
            spy.clear()
        self.all_emissions.clear()

    def wait_for_sequence(
        self,
        sequence: list[str],
        timeout_ms: int = 1000,
        ordered: bool = True
    ) -> bool:
        """
        Wait for a sequence of signal emissions.

        Args:
            sequence: List of signal names in expected order
            timeout_ms: Maximum wait time
            ordered: Whether signals must occur in exact order

        Returns:
            True if sequence detected, False if timeout
        """
        def check_sequence():
            if ordered:
                # Check exact order
                if len(self.all_emissions) < len(sequence):
                    return False

                for i, expected_name in enumerate(sequence):
                    if i >= len(self.all_emissions):
                        return False
                    if self.all_emissions[i].signal_name != expected_name:
                        return False
                return True
            # Check all signals present (any order)
            emitted_names = {e.signal_name for e in self.all_emissions}
            return all(name in emitted_names for name in sequence)

        return EventLoopHelper.wait_until(check_sequence, timeout_ms)

    def assert_sequence(
        self,
        sequence: list[str],
        timeout_ms: int = 1000,
        ordered: bool = True
    ):
        """
        Assert a sequence of signals was emitted.

        Args:
            sequence: Expected signal sequence
            timeout_ms: Time to wait for sequence
            ordered: Whether order matters
        """
        success = self.wait_for_sequence(sequence, timeout_ms, ordered)

        if not success:
            actual = [e.signal_name for e in self.all_emissions]
            raise AssertionError(f"Expected signal sequence {sequence} {'(ordered)' if ordered else '(any order)'}, got {actual}")

    def get_timeline(self) -> str:
        """
        Get timeline of all signal emissions.

        Returns:
            Formatted timeline string
        """
        if not self.all_emissions:
            return "No signals emitted"

        lines = ["Signal Timeline:"]
        for emission in sorted(self.all_emissions, key=lambda e: e.timestamp):
            lines.append(f"  {emission.timestamp:6.3f}s: {emission}")

        return "\n".join(lines)


class AsyncSignalTester:
    """Helper for testing async signal behavior."""

    @staticmethod
    @contextmanager
    def wait_for_signal(
        signal: Signal | SignalInstance,
        timeout_ms: int = 1000
    ) -> Generator[list[Any], None, None]:
        """
        Context manager to wait for signal emission.

        Args:
            signal: Signal to wait for
            timeout_ms: Maximum wait time

        Yields:
            List to collect signal arguments
        """
        result = []
        event_loop = QEventLoop()

        def on_signal(*args):
            result.extend(args)
            event_loop.quit()

        signal.connect(on_signal)

        # Setup timeout
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(event_loop.quit)
        timer.start(timeout_ms)

        try:
            yield result
            event_loop.exec()
        finally:
            signal.disconnect(on_signal)
            timer.stop()

    @staticmethod
    def emit_delayed(
        signal: Signal | SignalInstance,
        delay_ms: int,
        *args
    ) -> QTimer:
        """
        Emit a signal after a delay.

        Args:
            signal: Signal to emit
            delay_ms: Delay in milliseconds
            *args: Signal arguments

        Returns:
            Timer instance (for cancellation if needed)
        """
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: signal.emit(*args))
        timer.start(delay_ms)
        return timer

    @staticmethod
    def emit_sequence(
        signals: list[tuple[Signal | SignalInstance, tuple[Any, ...]]],
        interval_ms: int = 100
    ) -> list[QTimer]:
        """
        Emit a sequence of signals with delays.

        Args:
            signals: List of (signal, args) tuples
            interval_ms: Interval between emissions

        Returns:
            List of timers
        """
        timers = []

        for i, (signal, args) in enumerate(signals):
            delay = i * interval_ms
            timer = AsyncSignalTester.emit_delayed(signal, delay, *args)
            timers.append(timer)

        return timers


class CrossThreadSignalTester:
    """Helper for testing signals across threads."""

    @staticmethod
    def verify_thread_safety(
        signal: Signal | SignalInstance,
        emit_in_thread: bool = True,
        connect_in_thread: bool = False
    ) -> bool:
        """
        Verify signal is thread-safe.

        Args:
            signal: Signal to test
            emit_in_thread: Whether to emit from worker thread
            connect_in_thread: Whether to connect from worker thread

        Returns:
            True if thread-safe
        """
        result = {"success": False, "emissions": 0}

        class Worker(QObject):
            test_signal = Signal(int)

            def __init__(self):
                super().__init__()
                self.counter = 0

            def run(self):
                if emit_in_thread:
                    for i in range(10):
                        signal.emit(i)
                        QThread.msleep(1)

        def on_signal(value):
            result["emissions"] += 1
            if result["emissions"] == 10:
                result["success"] = True

        thread = QThread()
        worker = Worker()
        worker.moveToThread(thread)

        if connect_in_thread:
            thread.started.connect(lambda: signal.connect(on_signal))
        else:
            signal.connect(on_signal)

        thread.started.connect(worker.run)
        thread.start()

        # Wait for completion
        thread.wait(1000)

        return result["success"]

    @staticmethod
    def create_threaded_emitter(
        signal_type: Optional[type] = None
    ) -> tuple[QObject, QThread]:
        """
        Create an object that emits signals from a worker thread.

        Args:
            signal_type: Signal type to use (default: Signal(int))

        Returns:
            Tuple of (emitter object, thread)
        """
        class ThreadedEmitter(QObject):
            if signal_type:
                signal = signal_type
            else:
                signal = Signal(int)

            def emit_value(self, value):
                self.signal.emit(value)

        emitter = ThreadedEmitter()
        thread = QThread()
        emitter.moveToThread(thread)
        thread.start()

        return emitter, thread


class SignalValidator:
    """Validator for complex signal patterns."""

    def __init__(self):
        """Initialize validator."""
        self.rules: list[Callable[[SignalEmission], bool]] = []
        self.violations: list[str] = []

    def add_rule(
        self,
        rule: Callable[[SignalEmission], bool],
        description: str = "Custom rule"
    ):
        """
        Add validation rule.

        Args:
            rule: Function that returns True if emission is valid
            description: Rule description for error messages
        """
        def wrapped_rule(emission: SignalEmission) -> bool:
            if not rule(emission):
                self.violations.append(
                    f"{description} violated by {emission}"
                )
                return False
            return True

        self.rules.append(wrapped_rule)

    def add_rate_limit(
        self,
        max_rate: float,
        window_ms: int = 1000
    ):
        """
        Add rate limiting rule.

        Args:
            max_rate: Maximum emissions per second
            window_ms: Time window for rate calculation
        """
        emissions_window = deque()
        window_sec = window_ms / 1000.0

        def rate_rule(emission: SignalEmission) -> bool:
            nonlocal emissions_window

            # Remove old emissions outside window
            cutoff = emission.timestamp - window_sec
            while emissions_window and emissions_window[0] < cutoff:
                emissions_window.popleft()

            # Add current emission
            emissions_window.append(emission.timestamp)

            # Check rate
            rate = len(emissions_window) / window_sec
            return rate <= max_rate

        self.add_rule(rate_rule, f"Rate limit {max_rate}/sec")

    def add_sequence_rule(
        self,
        valid_sequences: list[list[str]]
    ):
        """
        Add rule for valid signal sequences.

        Args:
            valid_sequences: List of valid signal name sequences
        """
        recent_signals = deque(maxlen=max(len(seq) for seq in valid_sequences))

        def sequence_rule(emission: SignalEmission) -> bool:
            recent_signals.append(emission.signal_name)

            # Check if current sequence matches any valid sequence
            current = list(recent_signals)
            for valid_seq in valid_sequences:
                if current[-len(valid_seq):] == valid_seq:
                    return True

            # Allow if we don't have enough history yet
            return len(recent_signals) < min(len(seq) for seq in valid_sequences)

        self.add_rule(sequence_rule, f"Valid sequences: {valid_sequences}")

    def validate(self, spy: SignalSpy | MultiSignalSpy) -> bool:
        """
        Validate emissions against rules.

        Args:
            spy: Signal spy with emissions to validate

        Returns:
            True if all rules pass
        """
        self.violations.clear()

        if isinstance(spy, SignalSpy):
            emissions = spy.emissions
        else:
            emissions = spy.all_emissions

        for emission in emissions:
            for rule in self.rules:
                if not rule(emission):
                    return False

        return True

    def get_violations(self) -> list[str]:
        """Get list of rule violations."""
        return self.violations.copy()

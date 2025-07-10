#!/usr/bin/env python3
"""
Test to verify the cancellation issue in workers where error signals
might be emitted after cancellation.
"""

import os
import sys
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QEventLoop

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixel_editor_workers import FileLoadWorker


def test_cancellation_during_error():
    """Test that no signals are emitted after cancellation during error handling"""
    print("Testing cancellation during error handling...")
    
    signals_received = []
    
    def track_signal(signal_name):
        def handler(*args):
            signals_received.append((signal_name, time.time()))
        return handler
    
    # Create worker with non-existent file to trigger error
    worker = FileLoadWorker("/non/existent/file.png")
    worker.progress.connect(track_signal("progress"))
    worker.error.connect(track_signal("error"))
    worker.finished.connect(track_signal("finished"))
    
    # Start worker
    worker.start()
    
    # Cancel immediately (before error can be emitted)
    cancel_time = time.time()
    worker.cancel()
    
    # Wait a bit for worker to finish
    worker.wait(1000)
    
    # Check signals
    print(f"Signals received: {len(signals_received)}")
    for signal_name, signal_time in signals_received:
        time_diff = signal_time - cancel_time
        print(f"  {signal_name}: {time_diff:.3f}s after cancellation")
        
    # Check if any signals were emitted after cancellation
    post_cancel_signals = [(name, t) for name, t in signals_received if t > cancel_time]
    
    if post_cancel_signals:
        print(f"\n⚠️  ISSUE FOUND: {len(post_cancel_signals)} signals emitted after cancellation!")
        for signal_name, _ in post_cancel_signals:
            print(f"   - {signal_name}")
        return False
    else:
        print("\n✓ No signals emitted after cancellation")
        return True


if __name__ == "__main__":
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    app = QApplication.instance() or QApplication(sys.argv)
    
    result = test_cancellation_during_error()
    sys.exit(0 if result else 1)
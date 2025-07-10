#!/usr/bin/env python3
"""
Controller for sprite injection functionality
Manages interaction between inject tab view and sprite model
"""

import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sprite_editor.workers.inject_worker import InjectWorker

from .base_controller import BaseController


class InjectController(BaseController):
    """Controller for injection operations"""

    def __init__(self, sprite_model, project_model, inject_view, parent=None):
        super().__init__(sprite_model, inject_view, parent)
        self.project_model = project_model
        self.inject_worker = None

    def connect_signals(self):
        """Connect signals between model and view"""
        # View signals
        self.view.inject_requested.connect(self.inject_sprites)
        self.view.browse_png_requested.connect(self.browse_png_file)
        self.view.browse_vram_requested.connect(self.browse_vram_file)

        # Model signals
        self.model.vram_file_changed.connect(self.view.set_vram_file)

    def browse_png_file(self):
        """Browse for PNG file to inject"""
        file_name, _ = QFileDialog.getOpenFileName(
            self.view, "Select PNG File", "", "PNG Files (*.png);;All Files (*.*)"
        )

        if file_name:
            self.view.set_png_file(file_name)
            self.project_model.add_recent_file(file_name, "png")

            # Validate PNG
            self.validate_png(file_name)

    def browse_vram_file(self):
        """Browse for target VRAM file"""
        # Get initial directory from last file
        initial_dir = ""
        if self.model.vram_file and os.path.exists(
            os.path.dirname(self.model.vram_file)
        ):
            initial_dir = os.path.dirname(self.model.vram_file)

        file_name, _ = QFileDialog.getOpenFileName(
            self.view,
            "Select Target VRAM",
            initial_dir,
            "Dump Files (*.dmp);;All Files (*.*)",
        )

        if file_name:
            self.view.set_vram_file(file_name)
            self.model.vram_file = file_name
            self.project_model.add_recent_file(file_name, "vram")

    def validate_png(self, png_file):
        """Validate PNG file for SNES compatibility"""
        if not os.path.exists(png_file):
            return

        valid, issues = self.model.validate_png(png_file)

        if valid:
            self.view.set_validation_text("✓ PNG is valid for SNES conversion", True)
        else:
            self.view.set_validation_text(
                "✗ Issues found:\n" + "\n".join(issues), False
            )

    def inject_sprites(self):
        """Inject sprites into VRAM"""
        # Get parameters from view
        params = self.view.get_injection_params()

        # Validate inputs
        if not params["png_file"] or not os.path.exists(params["png_file"]):
            QMessageBox.warning(self.view, "Error", "Please select a valid PNG file")
            return

        if not params["vram_file"] or not os.path.exists(params["vram_file"]):
            QMessageBox.warning(self.view, "Error", "Please select a valid VRAM file")
            return

        # Prepare output file
        output_file = params["output_file"]
        if not output_file:
            output_file = "VRAM_edited.dmp"

        # Make full path
        if not os.path.isabs(output_file):
            output_file = os.path.join(
                os.path.dirname(params["vram_file"]), output_file
            )

        # Clear output
        self.view.clear_output()
        self.view.append_output("Starting injection...")

        # Create worker thread
        self.inject_worker = InjectWorker(
            params["png_file"], params["vram_file"], params["offset"], output_file
        )

        self.inject_worker.progress.connect(self.on_inject_progress)
        self.inject_worker.finished.connect(self.on_inject_finished)
        self.inject_worker.error.connect(self.on_inject_error)

        # Disable controls
        self.view.set_inject_enabled(False)

        # Start injection
        self.inject_worker.start()

    def on_inject_progress(self, message):
        """Handle injection progress"""
        self.view.append_output(message)

    def on_inject_finished(self, output_file):
        """Handle injection completion"""
        self.view.set_inject_enabled(True)

        self.view.append_output(f"\nSuccess! Created: {output_file}")
        self.view.append_output("You can now load this file in your emulator")

        QMessageBox.information(
            self.view,
            "Success",
            f"Sprites injected successfully!\n\nOutput: {output_file}",
        )

        # Mark project as modified
        self.project_model.mark_modified()

    def on_inject_error(self, error):
        """Handle injection error"""
        self.view.set_inject_enabled(True)
        self.view.append_output(f"\nError: {error}")
        QMessageBox.critical(self.view, "Injection Error", error)

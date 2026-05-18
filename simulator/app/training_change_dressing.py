"""
AR training module for epidural catheter dressing change.

This reuses the camera and hand-tracking foundation from the catheter removal
training, then replaces the later needle-removal phases with a new-dressing
placement task.
"""

from __future__ import annotations

import time
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.training_records import get_training_record_manager
from app.training_remove_needle import RemoveNeedleTraining


class ChangeDressingTraining(RemoveNeedleTraining):
    """Change dressing AR flow: prepare site, remove old dressing, apply new dressing."""

    def __init__(self, parent=None, training_mode="change_dressing"):
        super().__init__(parent=parent, training_mode=training_mode)
        self.training_mode = "change_dressing"
        self._change_dressing_stage = "intro"
        self.new_dressing_picked = False
        self.new_dressing_hold_start = None
        self.new_dressing_pinch_point = None
        self._change_dressing_complete_called = False

    def start_training(self):
        self.training_start_time = time.time()
        self._change_dressing_stage = "intro"
        self.current_phase = 0
        self.phase_transition_pending = False
        self._start_phase_1()

    def _start_phase_1(self):
        """Intro guidance for dressing change."""
        print("[ChangeDressingTraining] Starting phase 1")
        self.current_phase = 0
        self.show_phase1_icon = True

        guide_text = (
            "It is time to change the epidural catheter dressing. "
            "First, check the catheter marking and inspect the entry site. "
            "Then keep your hand steady on the model and prepare to remove the old dressing."
        )

        phase1_info_frame = QFrame(self)
        phase1_info_frame.setGeometry(100, 10, self.width() - 200, 200)
        phase1_info_frame.setStyleSheet(
            """
            QFrame {
                background: rgba(255, 255, 255, 0.72);
                border: 2px solid #FFFFFF;
                border-radius: 8px;
                padding: 16px;
            }
            """
        )

        info_layout = QVBoxLayout(phase1_info_frame)
        info_label = QLabel(guide_text)
        info_label.setStyleSheet(
            """
            QLabel {
                color: #003366;
                font-family: 'Segoe Print', 'Segoe UI', Arial;
                font-size: 23px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0;
            }
            """
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(info_label)
        phase1_info_frame.setVisible(True)
        phase1_info_frame.raise_()

        self.phase1_info_frame = phase1_info_frame
        self.text_display.setVisible(False)

        self.phase_timer = QTimer(self)
        self.phase_timer.setSingleShot(True)
        self.phase_timer.timeout.connect(self._transition_to_phase_2)
        self.phase_timer.start(8000)

    def _start_phase_2(self):
        self.current_phase = 1
        self.phase_transition_pending = False
        self.text_display.setVisible(True)
        self.text_display.set_text("Press and hold the catheter site to confirm the dressing-change field.")
        self.text_display.fade_in(duration_ms=500)
        self.pinch_start_time = None

    def _show_phase_3_content(self):
        self._change_dressing_stage = "remove_old"
        self.text_display.set_text("Remove the old dressing carefully by moving it away from the entry site.")
        self.text_display.fade_in(duration_ms=500)

        self.finger_left_time = None
        self.phase3_animation_start_time = None
        self.wipe_blood_start_time = None
        self.wipe_blood_duration = 5.0

    def _phase_3_update(self, frame, hand_data_list):
        if getattr(self, "_training_complete_called", False) or getattr(self, "_change_dressing_complete_called", False):
            return
        if self._change_dressing_stage != "apply_new" and getattr(self, "phase_transition_pending", False):
            return
        if self._change_dressing_stage == "apply_new":
            self._apply_new_dressing_update(frame, hand_data_list)
            return
        super()._phase_3_update(frame, hand_data_list)

    def _phase_3_success(self):
        """Old dressing removed; proceed to applying the new dressing."""
        if self.phase_transition_pending:
            return
        self.phase_transition_pending = True
        self.finger_left_time = None
        self.phase3_animation_start_time = None

        self.text_display.fade_out(duration_ms=300)
        QTimer.singleShot(300, lambda: self.success_display.show_success(
            audio_path=self.audio_success,
            duration_ms=1000,
        ))
        QTimer.singleShot(1300, self._start_apply_new_dressing)

    def _start_apply_new_dressing(self):
        self.current_phase = 2
        self.phase_transition_pending = False
        self._change_dressing_stage = "apply_new"
        self.new_dressing_picked = False
        self.new_dressing_hold_start = None
        self.new_dressing_pinch_point = None

        self.text_display.set_text(
            "Pick up the new sterile dressing, bring it back to the catheter site, and hold for 2 seconds."
        )
        self.text_display.fade_in(duration_ms=500)
        print("[ChangeDressingTraining] Apply-new-dressing phase started")

    def _apply_new_dressing_update(self, frame, hand_data_list):
        self._draw_hand_skeleton(frame, hand_data_list)

        h, w = frame.shape[:2]
        target_x, target_y = w // 2, h // 2
        source_x, source_y = int(w * 0.22), int(h * 0.76)
        now = time.time()

        pinch_point = self._get_pinched_hand_point(hand_data_list)
        if pinch_point:
            self.new_dressing_pinch_point = pinch_point

        cv2.circle(frame, (source_x, source_y), 48, (255, 190, 80), 2)
        cv2.circle(frame, (target_x, target_y), 56, (0, 160, 90), 3)

        source_label = "New dressing"
        target_label = "Apply here"
        cv2.putText(frame, source_label, (source_x - 80, source_y - 58), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 190, 80), 2)
        cv2.putText(frame, target_label, (target_x - 70, target_y - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 160, 90), 2)

        if self.medical_dressing_icon is not None:
            if self.new_dressing_picked and pinch_point:
                self._overlay_medical_dressing_with_animation(frame, int(pinch_point[0]), int(pinch_point[1]), 0, 0, 0.92)
            else:
                self._overlay_medical_dressing_with_animation(frame, source_x, source_y, 0, 0, 0.92)

        if pinch_point:
            px, py = pinch_point
            source_dist = float(np.sqrt((px - source_x) ** 2 + (py - source_y) ** 2))
            target_dist = float(np.sqrt((px - target_x) ** 2 + (py - target_y) ** 2))

            if not self.new_dressing_picked and source_dist < 120:
                self.new_dressing_picked = True
                self.text_display.set_text("New dressing picked up. Move it to the catheter site.")
                print("[ChangeDressingTraining] New dressing picked up")

            if self.new_dressing_picked and target_dist < 95:
                if self.new_dressing_hold_start is None:
                    self.new_dressing_hold_start = now
                    print("[ChangeDressingTraining] Holding new dressing at target")
                hold_elapsed = now - self.new_dressing_hold_start
                progress = min(1.0, hold_elapsed / 2.0)
                cv2.circle(frame, (target_x, target_y), int(60 + progress * 20), (0, 220, 120), 3)
                cv2.putText(
                    frame,
                    f"Hold {hold_elapsed:.1f}/2.0s",
                    (target_x - 95, target_y + 85),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.85,
                    (0, 220, 120),
                    2,
                )
                if hold_elapsed >= 2.0:
                    self._complete_change_dressing()
                    return
            else:
                self.new_dressing_hold_start = None
        else:
            self.new_dressing_hold_start = None

        instruction = "Pinch the new dressing, then place it on the green target"
        if self.new_dressing_picked:
            instruction = "Move the dressing to the green target and hold"
        cv2.putText(frame, instruction, (35, h - 38), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

    def _get_pinched_hand_point(self, hand_data_list):
        for hand_data in hand_data_list:
            joints = hand_data.get("joints", [])
            pinch_state = hand_data.get("pinch_state", {})
            if len(joints) <= 8 or not pinch_state.get("is_pinched"):
                continue
            thumb = joints[4]
            index = joints[8]
            tx = thumb.get("x", 0) if isinstance(thumb, dict) else thumb[0]
            ty = thumb.get("y", 0) if isinstance(thumb, dict) else thumb[1]
            ix = index.get("x", 0) if isinstance(index, dict) else index[0]
            iy = index.get("y", 0) if isinstance(index, dict) else index[1]
            return (float(tx + ix) / 2.0, float(ty + iy) / 2.0)
        return None

    def _complete_change_dressing(self):
        if self._change_dressing_complete_called:
            return
        self._change_dressing_complete_called = True
        self._change_dressing_stage = "complete"
        self.phase_transition_pending = True
        elapsed_time = time.time() - self.training_start_time if self.training_start_time else 0.0
        self._pass_elapsed_snapshot = elapsed_time

        self.text_display.set_text(f"Dressing changed successfully!\nTime: {elapsed_time:.1f}s")
        self.text_display.fade_in(duration_ms=500)
        self.success_display.show_success(audio_path=self.audio_success, duration_ms=2000)

        self._complete_timer = QTimer(self)
        self._complete_timer.setSingleShot(True)
        self._complete_timer.timeout.connect(self._complete_training)
        self._complete_timer.start(2500)

    def _complete_training(self):
        if getattr(self, "_training_complete_called", False):
            return
        self._training_complete_called = True
        self.setVisible(False)

        elapsed_time = getattr(self, "_pass_elapsed_snapshot", None)
        if elapsed_time is None:
            elapsed_time = time.time() - self.training_start_time if self.training_start_time else 0.0

        training_data = {
            "training_type": "change_dressing",
            "training_mode": "change_dressing",
            "procedure_name": "dressing_change",
            "procedure_attempt_count": 1,
            "procedure_completed": True,
            "elapsed_time": elapsed_time,
            "accuracy": 100.0,
            "completion_rate": 100.0,
            "expected_events": 3,
            "phase4_events_completed": 3,
            "events_triggered": {
                "field_confirmed": True,
                "old_dressing_removed": True,
                "new_dressing_applied": True,
            },
            "events_results": [
                {"question_id": "CD1", "trigger_time": 0.0, "correct": True},
                {"question_id": "CD2", "trigger_time": round(max(elapsed_time - 2.0, 0.0), 2), "correct": True},
                {"question_id": "CD3", "trigger_time": round(elapsed_time, 2), "correct": True},
            ],
            "completed_at": datetime.now().isoformat(),
        }

        try:
            username = getattr(self, "current_user", "unknown")
            manager = get_training_record_manager()
            manager.save_training_record(username, training_data)
            print(f"[ChangeDressingTraining] Record saved for {username}: time={elapsed_time:.1f}s")
        except Exception as exc:
            print(f"[ChangeDressingTraining] Error saving training record: {exc}")

        self.cleanup()
        self.training_completed.emit()

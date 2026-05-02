"""Debug replacement for ``RemoveNeedleTraining._phase_2_update``.

This helper is intentionally kept separate from the production training flow.
Use ``run_debug_test.py`` to copy the function below into
``training_remove_needle_mcu.py`` temporarily when diagnosing why the
"Press here" target is not being triggered.
"""


def _phase_2_update_debug(self, frame, hand_data_list):
    """Phase 2 debug update: hold the needle tip target for two seconds."""
    center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2
    is_pinching = False
    closest_distance = None

    print("[DEBUG] Entered _phase_2_update")
    print(f"[DEBUG] hands detected: {len(hand_data_list)}")
    print(f"[DEBUG] target center: ({center_x}, {center_y})")

    for index, hand_data in enumerate(hand_data_list):
        joints = hand_data.get("joints", [])
        print(f"[DEBUG] hand {index}: {len(joints)} joints")

        if not joints or len(joints) <= 8:
            continue

        index_tip = joints[8]
        fx = index_tip.get("x", 0) if isinstance(index_tip, dict) else index_tip[0]
        fy = index_tip.get("y", 0) if isinstance(index_tip, dict) else index_tip[1]
        fx, fy = int(fx), int(fy)

        distance = np.sqrt((fx - center_x) ** 2 + (fy - center_y) ** 2)
        closest_distance = distance if closest_distance is None else min(closest_distance, distance)
        print(f"[DEBUG] hand {index}: index_tip=({fx}, {fy}), distance={distance:.1f}px")

        if distance < 20:
            is_pinching = True
            print("[DEBUG] finger is inside target")
            break

        print("[DEBUG] finger is outside target; expected distance < 20px")

    current_time = time.time()

    if is_pinching:
        if self.pinch_start_time is None:
            self.pinch_start_time = current_time
            self.last_pinch_time = current_time
            print("[DEBUG] hold started")
        else:
            self.last_pinch_time = current_time

        elapsed = current_time - self.pinch_start_time
        print(f"[DEBUG] held for {elapsed:.2f}s / 2.00s")

        if elapsed >= 2.0:
            print(f"[DEBUG] phase 2 success after {elapsed:.2f}s")
            self._phase_2_success()
    else:
        if self.pinch_start_time is not None:
            time_since_last_pinch = current_time - self.last_pinch_time

            if time_since_last_pinch < 0.5:
                print(f"[DEBUG] temporary detection loss tolerated: {time_since_last_pinch:.2f}s")
            else:
                elapsed = current_time - self.pinch_start_time
                print(f"[DEBUG] finger released after {elapsed:.2f}s; resetting hold")
                self.pinch_start_time = None
                self.last_pinch_time = None
        else:
            self.last_pinch_time = None

    self._draw_hand_skeleton(frame, hand_data_list)

    cv2.circle(frame, (center_x, center_y), 15, (0, 100, 0), 1)

    if self.medical_dressing_icon is not None:
        self._overlay_medical_dressing_with_animation(frame, center_x, center_y, 0, 0, 1.0)

    if self.finger_icon is not None:
        self._overlay_png_on_circle(frame, center_x, center_y, 20)

    text = "Press here"
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, 1.2, 2)[0]
    text_x = center_x - text_size[0] // 2
    text_y = center_y - 80
    cv2.putText(frame, text, (text_x, text_y), font, 1.2, (0, 100, 0), 2)

    distance_text = "N/A" if closest_distance is None else f"{closest_distance:.1f}px"
    debug_text = f"Distance: {distance_text} | Phase: 2"
    cv2.putText(frame, debug_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

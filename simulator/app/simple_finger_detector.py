"""Simple OpenCV fallback detector for the AR training flow.

This is only used when MediaPipe cannot initialize. It provides a coarse
finger-tip point so the training UI can still exercise the AR target logic.
"""

import cv2
import numpy as np


class SimpleFingerDetector:
    """Detect a likely finger tip using skin-color segmentation and contours."""

    def __init__(self):
        self.last_finger_position = None
        self.position_history = []

    def detect_finger_tip(self, frame):
        """Return an ``(x, y)`` finger-tip coordinate, or ``None`` when not found."""
        try:
            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)

            lower_skin = np.array([0, 133, 77], dtype=np.uint8)
            upper_skin = np.array([255, 173, 127], dtype=np.uint8)
            skin_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
            skin_mask = cv2.GaussianBlur(skin_mask, (5, 5), 0)

            contours, _ = cv2.findContours(
                skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            contours = [c for c in contours if cv2.contourArea(c) > 1000]
            if not contours:
                return None

            max_contour = max(contours, key=cv2.contourArea)
            hull = cv2.convexHull(max_contour)
            if len(hull) < 5:
                return None

            hull_indices = cv2.convexHull(max_contour, returnPoints=False)
            if len(hull_indices) < 3:
                return None

            defects = cv2.convexityDefects(max_contour, hull_indices)
            finger_tip = self._choose_finger_tip(max_contour, hull, defects)
            if finger_tip is None:
                return None

            if self.last_finger_position:
                alpha = 0.85
                finger_tip = (
                    int(alpha * finger_tip[0] + (1 - alpha) * self.last_finger_position[0]),
                    int(alpha * finger_tip[1] + (1 - alpha) * self.last_finger_position[1]),
                )

            self.last_finger_position = finger_tip
            self.position_history.append(finger_tip)
            if len(self.position_history) > 15:
                self.position_history.pop(0)

            return finger_tip
        except Exception as e:
            print(f"[SimpleFingerDetector] Error: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _choose_finger_tip(self, contour, hull, defects):
        """Pick the upper-most plausible fingertip from hull/defect geometry."""
        if defects is not None and len(defects) > 0:
            defects_list = defects.reshape(-1, 4)
            defects_list = defects_list[defects_list[:, 3].argsort()[::-1]]
            if len(defects_list) >= 3:
                start = tuple(contour[defects_list[0][0]][0])
                end = tuple(contour[defects_list[0][1]][0])
                far = tuple(contour[defects_list[0][2]][0])
                return min([start, end, far], key=lambda p: p[1])

        moments = cv2.moments(hull)
        if moments["m00"] == 0:
            return None

        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
        best_score = 0
        best_point = None
        for point in hull:
            px, py = tuple(point[0])
            vertical_distance = cy - py
            total_distance = np.sqrt((px - cx) ** 2 + (py - cy) ** 2)
            score = vertical_distance * 2 + total_distance
            if vertical_distance > 0 and score > best_score:
                best_score = score
                best_point = (px, py)

        return best_point

    def draw_finger(self, frame, finger_tip):
        """Draw the detected finger-tip point on a preview frame."""
        if finger_tip:
            cv2.circle(frame, finger_tip, 15, (0, 255, 0), 2)
            cv2.circle(frame, finger_tip, 3, (0, 0, 255), -1)
            cv2.putText(
                frame,
                f"({finger_tip[0]}, {finger_tip[1]})",
                (finger_tip[0] + 20, finger_tip[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 0),
                1,
            )

        return frame


if __name__ == "__main__":
    detector = SimpleFingerDetector()
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        finger_tip = detector.detect_finger_tip(frame)
        if finger_tip:
            frame = detector.draw_finger(frame, finger_tip)

        cv2.imshow("Simple Finger Detector", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

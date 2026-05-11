import numpy as np
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment


class Track:
    _next_id = 0

    def __init__(self, bbox: list[float]):
        self.id = Track._next_id
        Track._next_id += 1
        self.bbox = bbox
        self.kf = self._build_kf(bbox)
        self.hits = 1
        self.no_match_count = 0
        self._stationary_streak = 0
        self.stationary = False

    def _build_kf(self, bbox: list[float]) -> KalmanFilter:
        kf = KalmanFilter(dim_x=4, dim_z=2)
        cx, cy = _center(bbox)

        # Constant-velocity model: state = [cx, cy, vx, vy]
        kf.F = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=float)
        kf.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=float)

        kf.R *= 10.0
        kf.P[2:, 2:] *= 1000.0  # high initial velocity uncertainty
        kf.Q[2:, 2:] *= 0.01

        kf.x[:2] = np.array([[cx], [cy]])
        return kf

    def predict(self):
        self.kf.predict()

    def update(self, bbox: list[float]):
        cx, cy = _center(bbox)
        self.kf.update(np.array([[cx], [cy]]))
        self.bbox = bbox
        self.hits += 1
        self.no_match_count = 0

        vx, vy = self.kf.x[2, 0], self.kf.x[3, 0]
        if np.sqrt(vx ** 2 + vy ** 2) < 15.0:
            self._stationary_streak += 1
        else:
            self._stationary_streak = 0

        self.stationary = self._stationary_streak >= 5

    @property
    def position(self) -> tuple[float, float]:
        return float(self.kf.x[0, 0]), float(self.kf.x[1, 0])


class Tracker:
    MAX_AGE = 10        # frames before a lost track is removed
    MIN_HITS = 2        # frames before a track is reported
    IOU_THRESHOLD = 0.3

    def __init__(self):
        self.tracks: list[Track] = []

    def update(self, detections: list[list[float]]) -> list[Track]:
        for t in self.tracks:
            t.predict()

        matched, unmatched_dets, unmatched_trks = self._match(detections)

        for t_idx, d_idx in matched:
            self.tracks[t_idx].update(detections[d_idx])

        for d_idx in unmatched_dets:
            self.tracks.append(Track(detections[d_idx]))

        for t_idx in unmatched_trks:
            self.tracks[t_idx].no_match_count += 1

        self.tracks = [t for t in self.tracks if t.no_match_count <= self.MAX_AGE]

        return [t for t in self.tracks if t.hits >= self.MIN_HITS]

    def _match(self, detections):
        if not self.tracks or not detections:
            return [], list(range(len(detections))), list(range(len(self.tracks)))

        iou_mat = np.zeros((len(self.tracks), len(detections)))
        for ti, track in enumerate(self.tracks):
            for di, det in enumerate(detections):
                iou_mat[ti, di] = _iou(track, det)

        t_ids, d_ids = linear_sum_assignment(-iou_mat)

        matched, used_t, used_d = [], set(), set()
        for ti, di in zip(t_ids, d_ids):
            if iou_mat[ti, di] >= self.IOU_THRESHOLD:
                matched.append((ti, di))
                used_t.add(ti)
                used_d.add(di)

        unmatched_trks = [i for i in range(len(self.tracks)) if i not in used_t]
        unmatched_dets = [i for i in range(len(detections)) if i not in used_d]

        return matched, unmatched_dets, unmatched_trks


def _center(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def _iou(track: Track, bbox: list[float]) -> float:
    cx, cy = track.position
    x1, y1, x2, y2 = track.bbox
    w, h = x2 - x1, y2 - y1
    pb = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]

    ix1, iy1 = max(pb[0], bbox[0]), max(pb[1], bbox[1])
    ix2, iy2 = min(pb[2], bbox[2]), min(pb[3], bbox[3])

    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    if inter == 0.0:
        return 0.0

    pred_area = (pb[2] - pb[0]) * (pb[3] - pb[1])
    det_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    return inter / (pred_area + det_area - inter)

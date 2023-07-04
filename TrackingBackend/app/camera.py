from __future__ import annotations
from app.utils import WorkerProcess
from .types import CameraState, EyeID
from multiprocessing import Value
from .config import CameraConfig
from queue import Queue
import ctypes
import cv2

# fmt: off
OPENCV_PARAMS = [
    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000,
]
# fmt: on


class Camera(WorkerProcess):
    def __init__(self, config: CameraConfig, eye_id: EyeID, image_queue: Queue[cv2.Mat]):
        super().__init__(name=f"Capture {str(eye_id.name).capitalize()}")
        # Synced variables
        self.image_queue: Queue[cv2.Mat] = image_queue
        self.state = Value(ctypes.c_int, CameraState.DISCONNECTED.value)
        # Unsynced variables
        self.eye_id: EyeID = eye_id
        self.config: CameraConfig = config
        self.current_capture_source: str = self.config.capture_source
        self.camera: cv2.VideoCapture = None  # type: ignore

    def __del__(self):
        super().__del__()

    def get_state(self) -> CameraState:
        return CameraState(self.state.get_obj().value)

    def set_state(self, state: CameraState) -> None:
        # since we cant sync enums directly, so we sync the value of the enum instead
        self.state.get_obj().value = state.value

    def run(self) -> None:
        if self.camera is None:
            self.camera = cv2.VideoCapture()

        while True:
            # If things aren't open, retry until they are. Don't let read requests come in any earlier than this,
            # otherwise we can deadlock ourselves.
            if self.config.capture_source != "":
                # if the camera is disconnected or the capture source has changed, reconnect
                if self.get_state() == CameraState.DISCONNECTED or self.current_capture_source != self.config.capture_source:
                    self.connect_camera()
                else:
                    self.get_camera_image()
            else:  # no capture source is defined yet, so we wait :3
                self.set_state(CameraState.DISCONNECTED)

    def connect_camera(self) -> None:
        self.set_state(CameraState.CONNECTING)
        self.current_capture_source = self.config.capture_source
        try:
            self.camera.setExceptionMode(True)
            # https://github.com/opencv/opencv/issues/23207
            self.camera.open(self.current_capture_source, cv2.CAP_FFMPEG, OPENCV_PARAMS)
            if self.camera.isOpened():
                self.set_state(CameraState.CONNECTED)
                self.logger.info("Camera connected!")
            else:
                raise cv2.error
        except (cv2.error, Exception):
            self.set_state(CameraState.DISCONNECTED)
            self.logger.info(f"Capture source {self.current_capture_source} not found, retrying")

    def get_camera_image(self) -> None:
        try:
            ret, frame = self.camera.read()
            if not ret:
                self.camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.logger.warning("Capture source problem, assuming camera disconnected, waiting for reconnect.")
                self.set_state(CameraState.DISCONNECTED)
                return
            frame_number: float = self.camera.get(cv2.CAP_PROP_POS_FRAMES)
            fps: float = self.camera.get(cv2.CAP_PROP_FPS)
            self.push_image_to_queue(frame, frame_number, fps)
        except (cv2.error, Exception):
            self.set_state(CameraState.DISCONNECTED)
            self.logger.warning("Failed to retrieve or push frame to queue, Assuming camera disconnected, waiting for reconnect.")

    def push_image_to_queue(self, frame: cv2.Mat, frame_number: float, fps: float) -> None:
        qsize: int = self.image_queue.qsize()
        if qsize > 1:
            self.logger.warning(f"CAPTURE QUEUE BACKPRESSURE OF {qsize}. CHECK FOR CRASH OR TIMING ISSUES IN ALGORITHM.")
            pass
        try:
            self.image_queue.put(frame)
            # self.image_queue.put((frame, frame_number, fps))
        except (Exception):
            self.logger.exception("Failed to push to camera capture queue!")

from .logger import get_logger
from .camera import Camera
from .config import EyeTrackConfig
from .types import EyeID, EyeData
from .eye_processor import EyeProcessor
from .visualizer import Visualizer
import queue

logger = get_logger()


class Tracker:
    def __init__(self, eye_id: EyeID, config: EyeTrackConfig, osc_queue: queue.Queue[EyeData]):
        self.eye_id = eye_id
        self.config = config
        self.osc_queue = osc_queue
        self.eye_config = (self.config.left_eye, self.config.right_eye)[bool(self.eye_id.value)]  # god i love python
        # Camera stuff
        self.image_queue: queue.Queue = queue.Queue()
        self.camera = Camera(self.eye_config, self.eye_id, self.image_queue)
        self.visualizer = Visualizer(self.image_queue, True)  # TODO: change to False when done testing and algos get implemented
        # EyeProcessor stuff
        self.eye_processor = EyeProcessor(self.image_queue, self.config.algorithm, self.eye_id)

    def __del__(self):
        self.stop()

    def start(self) -> None:
        self.camera.start()
        self.eye_processor.start()

    def stop(self) -> None:
        self.camera.stop()
        self.eye_processor.stop()

    def restart(self) -> None:
        self.camera.restart()
        self.eye_processor.restart()

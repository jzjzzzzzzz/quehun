import threading

from runtime.autoplay import AutoPlayController


def format_result(result):
    hand = ",".join(result.get("hand") or [])
    return (
        f"{result['action']}: discard={result.get('discard')} "
        f"index={result.get('tile_index')} click={result.get('click')} "
        f"low_conf={result.get('low_confidence_count')} "
        f"reason={result.get('reason')} hand=[{hand}]"
    )


class AutoPlayRunner:
    def __init__(
        self,
        config_path,
        dry_run=True,
        debug_dir=None,
        on_result=None,
        on_error=None,
        on_stopped=None,
    ):
        self.config_path = config_path
        self.dry_run = dry_run
        self.debug_dir = debug_dir
        self.on_result = on_result
        self.on_error = on_error
        self.on_stopped = on_stopped
        self._stop_event = threading.Event()
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="autoplay-runner", daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()

    def _run(self):
        controller = None
        try:
            delay = 1.0
            while not self._stop_event.is_set():
                try:
                    if controller is None:
                        controller = AutoPlayController(
                            config_path=self.config_path,
                            dry_run=self.dry_run,
                            debug_dir=self.debug_dir,
                        )
                        delay = max(0.05, float(controller.config.get("delay", 1.0)))
                    result = controller.step()
                    if self.on_result:
                        self.on_result(result)
                except Exception as exc:
                    if self.on_error:
                        self.on_error(exc)
                self._stop_event.wait(delay)
        finally:
            if self.on_stopped:
                self.on_stopped()

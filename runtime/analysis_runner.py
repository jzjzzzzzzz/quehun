import threading

from runtime.analyzer import AnalysisController


class AnalysisRunner:
    def __init__(
        self,
        config_path,
        auto_click=False,
        debug=False,
        on_result=None,
        on_error=None,
        on_status=None,
        on_stopped=None,
    ):
        self.config_path = config_path
        self.auto_click = auto_click
        self.debug = debug
        self.on_result = on_result
        self.on_error = on_error
        self.on_status = on_status
        self.on_stopped = on_stopped
        self._stop_event = threading.Event()
        self._refresh_event = threading.Event()
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="quehun-analysis-runner",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        self._refresh_event.set()

    def refresh(self):
        self._refresh_event.set()

    def _emit_status(self, status):
        if self.on_status:
            self.on_status(status)

    def _run(self):
        controller = None
        delay = 1.0
        backoff = 1.0
        try:
            while not self._stop_event.is_set():
                try:
                    if controller is None:
                        controller = AnalysisController(
                            config_path=self.config_path,
                            auto_click=self.auto_click,
                        )
                        controller.set_debug(self.debug)
                        delay = max(0.1, float(controller.config.get("delay", 1.0)))
                        backoff = max(
                            0.2,
                            float(
                                controller.config.get("analysis", {}).get(
                                    "error_backoff",
                                    1.0,
                                )
                            ),
                        )
                    self._emit_status("Capturing")
                    result = controller.step()
                    self._emit_status(result.get("status", "Analyzing"))
                    if self.on_result:
                        self.on_result(result)
                    wait_time = delay
                except Exception as exc:
                    self._emit_status("Error Recovering")
                    if self.on_error:
                        self.on_error(exc)
                    wait_time = backoff
                self._refresh_event.wait(wait_time)
                self._refresh_event.clear()
        finally:
            if self.on_stopped:
                self.on_stopped()

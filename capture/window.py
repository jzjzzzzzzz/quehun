from capture.screen import capture_screen


class WindowCapture:
    def __init__(self, region):
        self.region = region

    def grab(self):
        return capture_screen(self.region.get_region())

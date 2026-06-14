class CaptureRegion:
    def __init__(self, left=0, top=0, width=1280, height=720):
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def get_region(self):
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

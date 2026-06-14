from runtime.pipeline import Pipeline


class Controller:
    def __init__(self, pipeline=None, dry_run=True):
        self.pipeline = pipeline or Pipeline()
        self.dry_run = dry_run

    def step(self, frame):
        result = self.pipeline.process(frame)
        if not result:
            return None

        if self.dry_run:
            return result

        raise NotImplementedError("Screen clicking is not configured yet.")

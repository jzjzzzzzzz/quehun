class FrameSync:
    def __init__(self, required_matches=1):
        self.required_matches = required_matches
        self.last = None
        self.count = 0

    def update(self, hand):
        current = tuple(hand or [])

        if current == self.last:
            self.count += 1
        else:
            self.last = current
            self.count = 1

        return self.count >= self.required_matches

class StateTracker:
    def __init__(self, required_matches=2):
        self.required_matches = required_matches
        self.last_hand = None
        self.stable_count = 0

    def is_stable(self, hand):
        current = tuple(hand or [])

        if current == self.last_hand:
            self.stable_count += 1
        else:
            self.last_hand = current
            self.stable_count = 1

        return self.stable_count >= self.required_matches

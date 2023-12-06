from ...connection import db_manager


class EventAliases(dict):

    def __init__(self, step: int = 1):
        assert step >= 1, "Step should not be less than 1"
        self._step = step
        self._counter = step
        super().__init__()
        self.step()

    def __getitem__(self, item):
        if item not in self:
            return item
        else:
            return super().__getitem__(item)

    def step(self):
        if self._counter == self._step:
            new_aliases = db_manager.get_event_aliases()
            self.update(new_aliases)
            self._counter = 0
        self._counter += 1

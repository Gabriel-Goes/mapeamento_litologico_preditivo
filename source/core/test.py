class Test:
    def __init__(self):
        self._a = 1

    def get_a(self):
        return self._a

    def set_a(self, a):
        self._a = a

    a = property(get_a, set_a)

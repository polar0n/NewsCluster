class ModifyOnAccessInteger:
    '''
    ModifyOnAccessInteger is an integer class which increments the stored integer
    value when the .get method is called.
    '''

    def __init__(self, value: int=0):
        self.value = value
    

    def __call__(self):
        self.value += 1
        return self.value - 1


    def get(self):
        return self.value


    def set(self, value: int):
        self.value = value


if __name__ == '__main__':
    # Run tests
    a = ModifyOnAccessInteger(1)
    assert a() == 1
    assert a() == 2
    a.set(0)
    assert a() == 0
    assert a() == 1

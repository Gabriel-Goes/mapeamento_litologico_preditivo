from multiprocessing import Pool
import multiprocessing
import time


def func(x):
    return x*x


if __name__ == "__main__":
    with Pool(3) as p:

        print(p.map(func, [1, 2, 3]))


class Process(multiprocessing.Process):
    def __init__(self, id):
        super(Process, self).__init__()
        self.id = id

    def run(self):
        time.sleep(1)

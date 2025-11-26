# log_utils.py
import os
import sys
import datetime
import contextlib


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


@contextlib.contextmanager
def log_stdout(log_dir: str, base_name: str):
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{base_name}_{ts}.log")

    f = open(log_path, "w")
    tee_out = Tee(sys.stdout, f)
    tee_err = Tee(sys.stderr, f)
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = tee_out, tee_err

    try:
        print(f"[LOG] Registrando execução em: {log_path}")
        yield log_path
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        f.close()

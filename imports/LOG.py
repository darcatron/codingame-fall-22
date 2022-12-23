import sys


class LOG:
    @staticmethod
    def debug(msg: str) -> None:
        print(f'(DEBUG) {msg}', file=sys.stderr, flush=True)

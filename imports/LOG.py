import sys

class LOG:
    @staticmethod
    def debug(msg: str, prefix: str = '') -> None:
        print(f'{prefix} -- {msg}', file=sys.stderr, flush=True)

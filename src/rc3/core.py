import cmd
import sys
import termios
import tty
import asyncio

from .dispatch import dispatch


class LiveCLI(cmd.Cmd):
    prompt = ''

    def safePrint(self, msg='', end='\n', write_buffer=True):
        text = str(msg)
        if write_buffer and hasattr(self, 'buffer'):
            buf = self.buffer
            if getattr(buf, 'enabled', False) and text.strip():
                buf.captured.append(text.rstrip('\n'))
        print(text, end=end)

    def read_line_raw(self):
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            chars = []
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    break
                chars.append(ch)
            return ''.join(chars)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    async def run(self):
        while True:
            line = await asyncio.to_thread(self.read_line_raw)
            line = line.strip()
            if not line:
                continue

            buf = getattr(self, 'buffer', None)
            if buf is not None and getattr(buf, 'enabled', False):
                if not line.startswith(("view", "clear")):
                    buf.captured.append(line)

            stop = await asyncio.to_thread(self.onecmd, line)
            self.safePrint("", write_buffer=False)
            if stop:
                break

    def onecmd(self, line):
        return dispatch(self, line)

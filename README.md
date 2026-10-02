# C2E — Console Command Engine

C2E is a lightweight, async‑friendly console command framework for Python.  
It provides a raw‑mode terminal engine (`LiveCLI`) and a flexible command DSL for building interactive CLIs with subcommands, parameters, flags, and argument metadata.

C2E is extracted from the ServerWatcher CLI and generalized into a reusable standalone library.

---

## Features

- **Async console loop**  
  Uses `asyncio.to_thread` to keep the event loop responsive.

- **Raw terminal input**  
  Reads characters directly using `termios` and `tty.setraw`.

- **Command DSL**  
  Decorators for commands, children, parameters, flags, and argument metadata.

- **Automatic help generation**  
  Built‑in help for commands, subcommands, and argument‑level usage.

- **Dynamic parameter/flag injection**  
  Child functions receive parameter values and flag states via wrapped globals.

- **One-shot argv dispatch**
  `LiveCLI.run_argv()` maps the same command DSL to conventional shell arguments
  without changing the existing interactive parser.

- **View‑safe printing**  
  `safePrint()` integrates with external buffer systems without breaking terminal output.

- **Minimal dependencies**  
  Only Python standard library + optional MapRes for color formatting.

---

## Installation

```bash
pip install c2e
```

## Process Arguments

Use `run_argv()` to dispatch a single command with normal positional arguments,
`--options`, and boolean flags:

```python
from c2e import LiveCLI, command


@command('greet')
def greet(cli, name: str):
  cli.safePrint(f'Hello, {name}!')


if __name__ == '__main__':
  LiveCLI().run_argv(prog='example')
```

Existing `LiveCLI.onecmd()` and interactive `parse_line()` behavior remains
available unchanged.

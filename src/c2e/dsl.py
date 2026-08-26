from dataclasses import dataclass
import inspect

from mapres import res

COMMANDS = {}

# ------------------------------------------------------------
# Shared metadata structures
# ------------------------------------------------------------

@dataclass
class ParamSpec:
    name: str
    type_: type
    default: object
    func: callable
    desc: str | None

@dataclass
class FlagSpec:
    name: str
    func: callable
    desc: str | None

@dataclass
class ArgMeta:
    name: str
    params: list[str]
    flags: list[str]
    required_params: set[str]
    required_flags: set[str]


# ------------------------------------------------------------
# Base class for CommandSpec and ChildSpec
# ------------------------------------------------------------

class BaseSpec:
    def __init__(self, func):
        self.func = func
        self.params = {}
        self.flags = {}
        self.args_meta = {}
        self.desc = self._doc(func)

        self._extract_args_block()
        self._parse_args_meta()
        self._infer_arg_requirement()

    # ------------------------------
    # Docstring extraction
    # ------------------------------
    def _doc(self, f):
        d = f.__doc__
        return d.strip().splitlines()[0].strip() if d else None

    # ------------------------------
    # __args__ block extraction
    # ------------------------------
    def _extract_args_block(self):
        src = inspect.getsource(self.func)
        lines = src.splitlines()
        block = []
        in_block = False

        for line in lines:
            s = line.strip()
            if s.startswith('__args__'):
                in_block = True
                continue
            if in_block:
                if s.startswith(("'''", '"""')):
                    if not block:
                        continue
                    else:
                        break
                block.append(line)

        if block:
            raw = '\n'.join(l.strip() for l in block)
            setattr(self.func, '__args__', raw)

    # ------------------------------
    # Parse __args__ metadata
    # ------------------------------
    def _parse_args_meta(self):
        raw = getattr(self.func, '__args__', None)
        if not raw:
            return

        for line in raw.splitlines():
            s = line.strip()
            if not s:
                continue

            if ':' in s:
                arg, rest = s.split(':', 1)
                arg = arg.strip()
                tokens = [t.strip() for t in rest.split(',') if t.strip()]
            else:
                arg = s
                tokens = []

            params = []
            flags = []
            req_p = set()
            req_f = set()

            for t in tokens:
                required = True
                if t.startswith('[') and t.endswith(']'):
                    required = False
                    t = t[1:-1].strip()

                if t.startswith('--'):
                    f = t[2:]
                    flags.append(f)
                    if required:
                        req_f.add(f)
                else:
                    params.append(t)
                    if required:
                        req_p.add(t)

            self.args_meta[arg] = ArgMeta(arg, params, flags, req_p, req_f)

    # ------------------------------
    # Infer required/optional positional arg
    # ------------------------------
    def _infer_arg_requirement(self):
        sig = inspect.signature(self.func)
        ps = list(sig.parameters.values())

        if len(ps) == 1:
            self.requires_arg = False
            self.optional_arg = False
        elif len(ps) == 2:
            p = ps[1]
            if p.default is inspect._empty:
                self.requires_arg = True
                self.optional_arg = False
            else:
                self.requires_arg = False
                self.optional_arg = True
        else:
            self.requires_arg = False
            self.optional_arg = False

    # ------------------------------
    # Param decorator
    # ------------------------------
    def param(self, name, type=str, default=None):
        def deco(f):
            py = name.replace('-', '_')
            d = f.__doc__.strip().splitlines()[0].strip() if f.__doc__ else None
            self.params[py] = ParamSpec(name, type, default, f, d)
            return f
        return deco

    # ------------------------------
    # Flag decorator
    # ------------------------------
    def flag(self, name):
        def deco(f):
            py = name.replace('-', '_')
            d = f.__doc__.strip().splitlines()[0].strip() if f.__doc__ else None
            self.flags[py] = FlagSpec(name, f, d)
            return f
        return deco


# ------------------------------------------------------------
# ChildSpec (inherits BaseSpec)
# ------------------------------------------------------------

class ChildSpec(BaseSpec):
    def __init__(self, parent, name, func):
        self.parent = parent
        self.name = name
        super().__init__(func)


# ------------------------------------------------------------
# CommandSpec (inherits BaseSpec)
# ------------------------------------------------------------

class CommandSpec(BaseSpec):
    def __init__(self, name, func, namespace=False):
        self.name = name
        self.children = {}
        self.is_namespace = namespace
        super().__init__(func)

    def child(self, name):
        def deco(f):
            c = ChildSpec(self, name, f)
            self.children[name] = c
            setattr(self, name, c)
            return c
        return deco


# ------------------------------------------------------------
# DSL entry point
# ------------------------------------------------------------

class CommandDSL:
    def __call__(self, name, namespace=False):
        def deco(f):
            spec = CommandSpec(name, f, namespace=namespace)
            COMMANDS[name] = spec
            return spec
        return deco

command = CommandDSL()


# ------------------------------------------------------------
# ParsedArgs structure
# ------------------------------------------------------------

@dataclass
class ParsedArgs:
    sub: str | None
    pos: list[str]
    flags: dict[str, bool]
    params: dict[str, str]


# ------------------------------------------------------------
# Line parser
# ------------------------------------------------------------

def parse_line(raw):
    raw = raw.strip()
    if not raw:
        return ParsedArgs(None, [], {}, {})

    parts = raw.split()
    sub = parts[0]
    pos = []
    flags = {}
    params = {}

    for t in parts[1:]:
        if t.startswith('--'):
            flags[t[2:]] = True
        elif ':' in t:
            k, v = t.split(':', 1)
            params[k.lower()] = v
        else:
            pos.append(t)

    return ParsedArgs(sub, pos, flags, params)


# ------------------------------------------------------------
# Help generation (unchanged)
# ------------------------------------------------------------

def help_command(cmd):
    lines = []
    d = cmd.desc or 'No description'
    lines.append(res(f'<bold><yellow>{cmd.name}<reset>: <gray>{d}<reset>'))

    if cmd.children:
        if cmd.is_namespace:
            u = res(f'<aqua>Usage:<reset> <gold>{cmd.name}<reset> <dark_gray>\\<<reset>child<dark_gray>\\><reset>')
        else:
            u = res(f'<aqua>Usage:<reset> <gold>{cmd.name}<reset> <dark_gray>[<reset>child<dark_gray>]<reset>')
    else:
        u = res(f'<aqua>Usage:<reset> <gold>{cmd.name}<reset>')

    if cmd.flags:
        u += res(' <dark_gray>[<reset>--flags<dark_gray>]<reset>')

    lines.append(u)

    if cmd.flags:
        lines.append('')
        lines.append(res('\0    <light_purple>Flags:<reset>'))
        for n, fs in cmd.flags.items():
            d = fs.desc or 'No description'
            lines.append(res(f'\0        <blue>--{fs.name}<reset>: <gray>{d}<reset>'))

    if cmd.children:
        lines.append('')
        lines.append(res('\0    <light_purple>Children:<reset>'))
        for n, c in cmd.children.items():
            cd = c.desc or 'No description'
            lines.append(res(f'\0        <green>{n}<reset>: <gray>{cd}<reset>'))

    return '\n'.join(lines)


def help_child(child):
    lines = []
    d = child.desc or 'No description'
    p = child.parent.name
    lines.append(res(f'<bold><green>{child.name}<reset>: <gray>{d}<reset>'))

    u = res(f'<aqua>Usage:<reset> <gold>{p}<reset> <green>{child.name}<reset>')
    if child.requires_arg:
        u += res(' <dark_gray>\\<<reset>arg<dark_gray>\\><reset>')
    elif child.optional_arg:
        u += res(' <dark_gray>[<reset>arg<dark_gray>]<reset>')
    if child.params:
        u += res(' <dark_gray>[<reset>params<dark_gray>]<reset>')
    if child.flags:
        u += res(' <dark_gray>[<reset>--flags<dark_gray>]<reset>')
    lines.append(u)

    if child.args_meta:
        lines.append('')
        lines.append(res('\0    <light_purple>Args:<reset>'))
        for a, m in child.args_meta.items():
            parts = [res(f'<green>{a}<reset>')]
            for pn in m.params:
                parts.append(res(f'<dark_gray>[<reset>{pn}<dark_gray>]<reset>'))
            for fn in m.flags:
                parts.append(res(f'<dark_gray>[<reset>--{fn}<dark_gray>]<reset>'))
            lines.append('\0        ' + ' '.join(parts))

    if child.params:
        lines.append('')
        lines.append(res('\0    <light_purple>Params:<reset>'))
        for n, ps in child.params.items():
            t = ps.type_.__name__
            d = ps.desc or 'No description'
            lines.append(res(f'\0        <blue>{n}<reset> (type=<gold>{t}<reset>, default=<gray>{ps.default}<reset>): <gray>{d}<reset>'))

    if child.flags:
        lines.append('')
        lines.append(res('\0    <light_purple>Flags:<reset>'))
        for n, fs in child.flags.items():
            d = fs.desc or 'No description'
            lines.append(res(f'\0        <blue>--{fs.name}<reset>: <gray>{d}<reset>'))

    return '\n'.join(lines)


def help_arg(child, meta):
    lines = []
    p = child.parent.name
    a = meta.name
    lines.append(res(f'<bold><aqua>{a}<reset>: <gray>Retrieve and print the {a} of the server<reset>'))

    u = res(f'<aqua>Usage:<reset> <gold>{p}<reset> <green>{child.name}<reset> <aqua>{a}<reset>')
    req = []
    opt = []

    for pn in meta.params:
        ps = child.params.get(pn)
        t = ps.type_.__name__ if ps else 'str'
        if pn in meta.required_params:
            req.append(res(f'<dark_gray>\\<<reset>{pn}:{t}<dark_gray>\\><reset>'))
        else:
            opt.append(res(f'<dark_gray>[<reset>{pn}:{t}<dark_gray>]<reset>'))

    if req:
        u += ' ' + ' '.join(req)
    if opt:
        u += ' ' + ' '.join(opt)

    if meta.flags:
        u += res(' <dark_gray>[<reset>--flags<dark_gray>]<reset>')

    lines.append(u)

    if meta.params:
        lines.append('')
        lines.append(res('\0    <light_purple>Params:<reset>'))
        for pn in meta.params:
            ps = child.params.get(pn)
            if not ps:
                continue
            t = ps.type_.__name__
            d = ps.desc or 'No description'
            lines.append(res(f'\0        <blue>{pn}<reset> (type=<gold>{t}<reset>, default=<gray>{ps.default}<reset>): <gray>{d}<reset>'))

    if meta.flags:
        lines.append('')
        lines.append(res('\0    <light_purple>Flags:<reset>'))
        for fn in meta.flags:
            fs = child.flags.get(fn)
            if not fs:
                continue
            d = fs.desc or 'No description'
            lines.append(res(f'\0        <blue>--{fn}<reset>: <gray>{d}<reset>'))

    return '\n'.join(lines)

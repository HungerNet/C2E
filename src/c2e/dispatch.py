import argparse
import inspect
import sys

from mapres import res
from .dsl import COMMANDS, parse_line, help_command, help_child, help_arg


def help_cmd_arg(cmd, meta):
    lines = []
    a = meta.name
    lines.append(res(f'<bold><aqua>{a}<reset>: <gray>Retrieve and print the {a} of the server<reset>'))

    u = res(f'<aqua>Usage:<reset> <gold>{cmd.name}<reset> <aqua>{a}<reset>')
    req = []
    opt = []

    for pn in meta.params:
        ps = cmd.params.get(pn)
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
            ps = cmd.params.get(pn)
            if not ps:
                continue
            t = ps.type_.__name__
            d = ps.desc or 'No description'
            lines.append(
                res(f'\0        <blue>{pn}<reset> (type=<gold>{t}<reset>, default=<gray>{ps.default}<reset>): <gray>{d}<reset>')
            )

    if meta.flags:
        lines.append('')
        lines.append(res('\0    <light_purple>Flags:<reset>'))
        for fn in meta.flags:
            fs = cmd.flags.get(fn)
            if not fs:
                continue
            d = fs.desc or 'No description'
            lines.append(res(f'\0        <blue>--{fn}<reset>: <gray>{d}<reset>'))

    return '\n'.join(lines)


def dispatch(cli, line):
    p = parse_line(line)
    if not p.sub:
        return

    cmd = COMMANDS.get(p.sub)
    if not cmd:
        return cli.safePrint(res(f'<red>Error:<reset> <gray>Unknown command {p.sub}<reset>'))

    # top-level help (no args)
    if 'help' in p.flags and not p.pos:
        return cli.safePrint(help_command(cmd))

    # ------------------------------------------------------------
    # CASE 1: command has children → existing child logic
    # ------------------------------------------------------------
    if cmd.children:
        if not p.pos:
            return cli.safePrint(res('<red>Error:<reset> <gray>Missing subcommand<reset>'))

        cname = p.pos[0]
        child = cmd.children.get(cname)
        if not child:
            return cli.safePrint(res(f'<red>Error:<reset> <gray>Unknown subcommand {cname}<reset>'))

        if 'help' in p.flags and len(p.pos) == 1:
            return cli.safePrint(help_child(child))

        if 'help' in p.flags and len(p.pos) >= 2:
            an = p.pos[1]
            meta = child.args_meta.get(an)
            if not meta:
                return cli.safePrint(res(f'<red>Error:<reset> <gray>Unknown argument {an}<reset>'))
            return cli.safePrint(help_arg(child, meta))

        arg = p.pos[1] if len(p.pos) > 1 else None
        if child.requires_arg and arg is None:
            return cli.safePrint(
                res(f'<red>Error:<reset> <gray>Subcommand {child.name} requires an argument<reset>')
            )

        g = child.func.__globals__

        for n, ps in child.params.items():
            if n in p.params:
                try:
                    v = ps.type_(p.params[n])
                except Exception:
                    v = ps.default
            else:
                v = ps.default

            def wrap(f=ps.func, val=v):
                def w():
                    return f(val)
                return w

            g[n] = wrap()

        for n, fs in child.flags.items():
            present = n in p.flags

            def wrap(f=fs.func, pr=present):
                def w():
                    return pr
                return w

            g[n] = wrap()

        f = child.func
        if f.__code__.co_argcount >= 2:
            return f(cli, arg)
        return f(cli)

    # ------------------------------------------------------------
    # CASE 2: command has NO children → treat like child
    # ------------------------------------------------------------
    arg = p.pos[0] if p.pos else None

    # arg-level help for top-level commands
    if 'help' in p.flags and arg is not None:
        meta = cmd.args_meta.get(arg)
        if not meta:
            return cli.safePrint(res(f'<red>Error:<reset> <gray>Unknown argument {arg}<reset>'))
        return cli.safePrint(help_cmd_arg(cmd, meta))

    # command-level help (no arg)
    if 'help' in p.flags and arg is None:
        return cli.safePrint(help_command(cmd))

    if cmd.requires_arg and arg is None:
        return cli.safePrint(
            res(f'<red>Error:<reset> <gray>Command {cmd.name} requires an argument<reset>')
        )

    g = cmd.func.__globals__

    for n, ps in cmd.params.items():
        if n in p.params:
            try:
                v = ps.type_(p.params[n])
            except Exception:
                v = ps.default
        else:
            v = ps.default

        def wrap(f=ps.func, val=v):
            def w():
                return f(val)
            return w

        g[n] = wrap()

    for n, fs in cmd.flags.items():
        present = n in p.flags

        def wrap(f=fs.func, pr=present):
            def w():
                return pr
            return w

        g[n] = wrap()

    f = cmd.func
    if f.__code__.co_argcount >= 2:
        return f(cli, arg)
    return f(cli)


def dispatch_argv(cli, argv=None, *, prog='c2e', description=None, default_command=None):
    """Dispatch process-style argv while leaving the interactive parser unchanged."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if (
        default_command
        and arguments
        and arguments[0] not in COMMANDS
        and arguments[0] not in {'-h', '--help'}
    ):
        arguments.insert(0, default_command)

    parser = argparse.ArgumentParser(prog=prog, description=description)
    subparsers = parser.add_subparsers(dest='_c2e_command', required=True)

    def add_options(command_parser, spec):
        signature = inspect.signature(spec.func)
        positional_parameters = list(signature.parameters.values())[1:]
        positional_parameters = [
            parameter
            for parameter in positional_parameters
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]

        for parameter in positional_parameters:
            annotation = parameter.annotation
            argument_type = annotation if isinstance(annotation, type) else str
            options = {'type': argument_type}
            if parameter.default is not inspect.Parameter.empty:
                options['nargs'] = '?'
                options['default'] = parameter.default
            command_parser.add_argument(parameter.name, **options)

        for name, param in spec.params.items():
            command_parser.add_argument(
                f'--{param.name}',
                dest=name,
                type=param.type_,
                default=param.default,
                help=param.desc,
            )

        for name, flag in spec.flags.items():
            command_parser.add_argument(
                f'--{flag.name}',
                dest=name,
                action='store_true',
                help=flag.desc,
            )

        command_parser.set_defaults(_c2e_spec=spec)

    for spec in COMMANDS.values():
        command_parser = subparsers.add_parser(spec.name, help=spec.desc)
        if spec.children:
            children = command_parser.add_subparsers(dest='_c2e_child', required=True)
            for child in spec.children.values():
                child_parser = children.add_parser(child.name, help=child.desc)
                add_options(child_parser, child)
        else:
            add_options(command_parser, spec)

    parsed = parser.parse_args(arguments)
    spec = parsed._c2e_spec
    signature = inspect.signature(spec.func)
    positional_names = [
        parameter.name
        for parameter in list(signature.parameters.values())[1:]
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    positional_values = [getattr(parsed, name) for name in positional_names]

    globals_ = spec.func.__globals__
    for name, param in spec.params.items():
        value = getattr(parsed, name)

        def wrap(func=param.func, val=value):
            return func(val)

        globals_[name] = wrap

    for name, flag in spec.flags.items():
        present = getattr(parsed, name)

        def wrap(func=flag.func, enabled=present):
            return func(enabled)

        globals_[name] = wrap

    return spec.func(cli, *positional_values)

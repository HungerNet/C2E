from mapres import res
from .dsl import COMMANDS, parse_line, help_command, help_child, help_arg


def dispatch(cli, line):
    p = parse_line(line)
    if not p.sub:
        return

    cmd = COMMANDS.get(p.sub)
    if not cmd:
        return cli.safePrint(res(f'<red>Error:<reset> <gray>Unknown command {p.sub}<reset>'))

    if 'help' in p.flags and not p.pos:
        return cli.safePrint(help_command(cmd))

    if cmd.children:
        if not p.pos:
            return cli.safePrint(res('<red>Error:<reset> <gray>Missing subcommand<reset>'))
    else:
        return cmd.func(cli)

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
        return cli.safePrint(res(f'<red>Error:<reset> <gray>Subcommand {child.name} requires an argument<reset>'))

    g = child.func.__globals__
    for n, ps in child.params.items():
        if n in p.params:
            try:
                v = ps.type_(p.params[n])
            except:
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

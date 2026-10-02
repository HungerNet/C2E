'''Tests for one-shot argv dispatch and legacy interactive parsing.'''

from types import SimpleNamespace

from c2e.dispatch import dispatch_argv
from c2e.dsl import COMMANDS, command, parse_line


def test_argv_dispatches_positionals_params_and_flags():
    '''Dispatch conventional arguments through the command DSL.'''
    previous = COMMANDS.get('test-argv')
    output = []

    @command('test-argv')
    def handler(cli, message: str):
        cli.safePrint(f'{message}:{count()}:{enabled()}')

    handler.param('count', type=int, default=2)(lambda value: value)
    handler.flag('enabled')(lambda value: value)

    try:
        cli = SimpleNamespace(safePrint=output.append)
        dispatch_argv(
            cli,
            ['test-argv', 'hello', '--count', '4', '--enabled'],
        )
        assert output == ['hello:4:True']
    finally:
        if previous is None:
            COMMANDS.pop('test-argv', None)
        else:
            COMMANDS['test-argv'] = previous


def test_legacy_parse_line_keeps_custom_syntax():
    '''Keep the existing interactive token syntax unchanged.'''
    parsed = parse_line('scan sample.bin --verbose depth:2')

    assert parsed.sub == 'scan'
    assert parsed.pos == ['sample.bin']
    assert parsed.flags == {'verbose': True}
    assert parsed.params == {'depth': '2'}
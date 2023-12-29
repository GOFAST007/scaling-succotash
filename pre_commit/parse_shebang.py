from __future__ import annotations

import os.path
from collections.abc import Mapping
from typing import NoReturn

from identify.identify import parse_shebang_from_file


class ExecutableNotFoundError(OSError):
    def to_output(self) -> tuple[int, bytes, None]:
        return (1, self.args[0].encode(), None)


def parse_filename(filename: str) -> tuple[str, ...]:
    if not os.path.exists(filename):
        return ()
    else:
        return parse_shebang_from_file(filename)


def find_executable(
        exe: str, *, env: Mapping[str, str] | None = None,
) -> str | None:
    exe = os.path.normpath(exe)
    if os.sep in exe:
        return exe

    environ = env if env is not None else os.environ

    if 'PATHEXT' in environ:
        exts = environ['PATHEXT'].split(os.pathsep)
        possible_exe_names = tuple(f'{exe}{ext}' for ext in exts) + (exe,)
    else:
        possible_exe_names = (exe,)

    for path in environ.get('PATH', '').split(os.pathsep):
        for possible_exe_name in possible_exe_names:
            joined = os.path.join(path, possible_exe_name)
            if os.path.isfile(joined) and os.access(joined, os.X_OK):
                return joined
    else:
        return None


def normexe(orig: str, *, env: Mapping[str, str] | None = None) -> str:
    def _error(msg: str) -> NoReturn:
        raise ExecutableNotFoundError(f'Executable `{orig}` {msg}')

    if os.sep not in orig and (not os.altsep or os.altsep not in orig):
        exe = find_executable(orig, env=env)
        if exe is None:
            _error('not found')
        return exe
    elif os.path.isdir(orig):
        _error('is a directory')
    elif not os.path.isfile(orig):
        _error('not found')
    elif not os.access(orig, os.X_OK):  # pragma: win32 no cover
        _error('is not executable')
    else:
        return orig


def normalize_cmd(
        cmd: tuple[str, ...],
        *,
        env: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Fixes for the following issues on windows
    - https://bugs.python.org/issue8557
    - windows does not parse shebangs

    This function also makes deep-path shebangs work just fine
    """
    # Use PATH to determine the executable
    exe = normexe(cmd[0], env=env)

    # Figure out the shebang from the resulting command
    cmd = parse_filename(exe) + (exe,) + cmd[1:]

    # This could have given us back another bare executable
    exe = normexe(cmd[0], env=env)

    return (exe,) + cmd[1:]

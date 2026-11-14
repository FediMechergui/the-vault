"""Discover host MATLAB and load its matching Engine API without copying licenses."""
from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


class MatlabSetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Installation:
    root: Path

    @property
    def engine_dir(self):
        return self.root / 'extern' / 'engines' / 'python'

    @property
    def release(self):
        match = re.search(r'R\d{4}[ab]', self.root.name)
        return match.group() if match else 'custom installation'


def registry_roots():
    if sys.platform != 'win32':
        return []
    import winreg
    roots = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, r'SOFTWARE\MathWorks\MATLAB', 0, winreg.KEY_READ | view) as key:
                    for index in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            with winreg.OpenKey(key, winreg.EnumKey(key, index)) as version:
                                roots.append(Path(winreg.QueryValueEx(version, 'MATLABROOT')[0]))
                        except OSError:
                            continue
            except OSError:
                continue
    return roots


def standard_roots():
    if sys.platform == 'win32':
        parents = [Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'MATLAB',
                   Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Programs' / 'MATLAB']
        return registry_roots() + [p for parent in parents for p in parent.glob('R20*')]
    if sys.platform == 'darwin':
        return list(Path('/Applications').glob('MATLAB_R20*.app')) + list((Path.home() / 'Applications').glob('MATLAB_R20*.app'))
    return [p for base in (Path('/usr/local/MATLAB'), Path('/opt/MATLAB'), Path('/opt/matlab'), Path.home() / 'MATLAB')
            for p in base.glob('R20*')]


def valid_root(root):
    return any((root / 'bin' / exe).is_file() for exe in ('matlab.exe', 'matlab')) and (root / 'extern/engines/python').is_dir()


def discover(root=None):
    explicit = root or os.environ.get('MATLAB_ROOT')
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not valid_root(path):
            raise MatlabSetupError(f'MATLAB_ROOT is not a complete desktop MATLAB installation: {path}')
        return Installation(path)
    executable = shutil.which('matlab')
    if executable:
        path = Path(executable).resolve().parent.parent
        if valid_root(path):
            return Installation(path)
    candidates = sorted(set(standard_roots()), key=lambda p: (re.findall(r'R\d{4}[ab]', str(p)) or [''])[0], reverse=True)
    for path in candidates:
        if valid_root(path):
            return Installation(path.resolve())
    return None


def select_backend(requested='auto', root=None):
    if requested == 'python-reference':
        return requested, None
    if requested not in ('auto', 'matlab-engine'):
        raise MatlabSetupError(f'Unsupported host backend: {requested}')
    installation = discover(root)
    if installation:
        return 'matlab-engine', installation
    if requested == 'matlab-engine':
        raise MatlabSetupError('No complete desktop MATLAB installation found. Set MATLAB_ROOT to its installation folder.')
    return 'python-reference', None


def engine_environment(installation, base=None):
    env = dict(os.environ if base is None else base)
    root = installation.root
    env['MATLAB_ROOT'] = str(root)
    env['PATH'] = os.pathsep.join([str(root / 'bin'), str(root / 'bin/win64'), env.get('PATH', '')])
    preinstalled = installation.engine_dir / 'dist'
    if (preinstalled / 'matlab/engine/__init__.py').is_file():
        env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(preinstalled), env.get('PYTHONPATH', '')]))
    if sys.platform != 'win32':
        arch = ('maca64' if platform.machine() == 'arm64' else 'maci64') if sys.platform == 'darwin' else 'glnxa64'
        name = 'DYLD_LIBRARY_PATH' if sys.platform == 'darwin' else 'LD_LIBRARY_PATH'
        env[name] = os.pathsep.join(filter(None, [str(root / 'bin' / arch), str(root / 'extern/bin' / arch), env.get(name, '')]))
    return env


def prepare_engine(installation, workspace):
    """Prefer the shipped API (R2026a+), otherwise install the bundled matching API."""
    env = engine_environment(installation)
    preinstalled = (installation.engine_dir / 'dist/matlab/engine/__init__.py').is_file()
    probe = subprocess.run([sys.executable, '-c', 'import matlab.engine'], env=env, capture_output=True, text=True)
    if probe.returncode == 0:
        return env
    if not preinstalled:
        if sys.prefix == sys.base_prefix:
            raise MatlabSetupError('Run with the project virtual environment; Engine setup will not modify global Python.')
        pip = subprocess.run([sys.executable, '-m', 'pip', '--version'], env=env, capture_output=True)
        if pip.returncode:
            seeded = subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], env=env)
            if seeded.returncode:
                raise MatlabSetupError('Install pip in the project virtual environment before configuring MATLAB Engine.')
        print(f'Installing the Engine API bundled with {installation.release} into the project environment.', flush=True)
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', '--force-reinstall',
                                 '--no-deps', str(installation.engine_dir)], env=env)
        if result.returncode:
            raise MatlabSetupError('Engine API installation failed. Check Python/MATLAB compatibility and installation-folder permissions. See docs/matlab.md.')
    probe = subprocess.run([sys.executable, '-c', 'import matlab.engine'], env=env, capture_output=True, text=True)
    if probe.returncode:
        raise MatlabSetupError('The installed MATLAB Engine API could not load. Use a supported 64-bit Python version with matching CPU architecture.\n' + probe.stderr[-2000:])
    return env


_dll_handles = []


def open_engine():
    """Start a private session; MATLAB itself checks the current user's activation."""
    expected = os.environ.get('MATLAB_ROOT')
    if expected:
        root = Path(expected).resolve()
        preinstalled = root / 'extern/engines/python/dist'
        if (preinstalled / 'matlab/engine/__init__.py').is_file():
            sys.path.insert(0, str(preinstalled))
        if sys.platform == 'win32':
            for folder in (root / 'bin/win64', root / 'extern/bin/win64'):
                if folder.is_dir():
                    _dll_handles.append(os.add_dll_directory(str(folder)))
    try:
        api = importlib.import_module('matlab.engine')
        engine = api.start_matlab('-nodesktop -nosplash')
    except Exception as exc:
        raise MatlabSetupError('MATLAB could not start using this OS user\'s existing license. Open desktop MATLAB as this user and resolve its activation error first.') from exc
    try:
        actual = Path(engine.matlabroot(nargout=1)).resolve()
        if expected and actual != Path(expected).resolve():
            raise MatlabSetupError('The Python Engine API started a different MATLAB release. Reinstall the API from the selected MATLAB_ROOT/extern/engines/python folder.')
        engine.addpath(str(Path(__file__).parent / 'src'), nargout=0)
        details = json.loads(engine.vault_engine_check(nargout=1))
        return engine, details
    except Exception as exc:
        engine.quit()
        if isinstance(exc, MatlabSetupError):
            raise
        raise MatlabSetupError('MATLAB started, but the scoring preflight failed. This project needs licensed Signal Processing Toolbox and Statistics and Machine Learning Toolbox. See the MATLAB error above.') from exc

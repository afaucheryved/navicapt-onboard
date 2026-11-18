"""Installer/désinstaller NaviCapt dans le profil utilisateur de Thonny, sans pip ni sudo."""
import argparse
from pathlib import Path
import shutil


def default_target():
    try:
        import thonny
    except ImportError:
        raise SystemExit('Exécuter ce script avec le Python qui contient Thonny (ex. /usr/bin/python3).')
    return Path(thonny.get_sys_path_directory_containg_plugins())


def install(target, uninstall=False):
    root = Path(__file__).resolve().parents[1]
    destination = target / 'thonnycontrib' / 'navicapt'
    if uninstall:
        if destination.exists():
            shutil.rmtree(destination)
        print('Extension NaviCapt retirée :', destination)
    else:
        shutil.copytree(root / 'thonny_plugin/thonnycontrib/navicapt', destination,
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        runtime = destination / 'runtime'
        runtime.mkdir(exist_ok=True)
        (runtime / '__init__.py').write_text('', encoding='utf-8')
        for name in ('pico_viewer.py', 'boat_view.py', 'telemetry.py'):
            shutil.copy2(root / 'src' / name, runtime / name)
        print('Extension NaviCapt installée :', destination)
    print('Fermer puis rouvrir Thonny pour appliquer le changement.')
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--target', type=Path, help='Dossier des modules d’extension (tests/profil personnalisé).')
    args = parser.parse_args()
    install(args.target if args.target is not None else default_target(), args.uninstall)


if __name__ == '__main__':
    main()

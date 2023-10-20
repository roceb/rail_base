import glob
from rail.cli import scripts
from rail.cli.options import GitMode

def test_render_nb():
    nb_files = glob.glob('../examples/*_examples/*.ipynb')
    scripts.render_nb('docs', False, True, nb_files, skip=None)
    scripts.render_nb('docs', True, True, nb_files, skip=None)


def test_clone_source():
    scripts.clone_source('..', GitMode.ssh, True, 'rail_packages.yml')
    scripts.clone_source('..', GitMode.https, True, 'rail_packages.yml')
    scripts.clone_source('..', GitMode.cli, True, 'rail_packages.yml')

    
def test_update_source():
    scripts.update_source('..', True, 'rail_packages.yml')


def test_install():
    scripts.install('..', False, True, 'rail_packages.yml')
    scripts.install('..', True, True, 'rail_packages.yml')


def test_info():
    scripts.info(print_all=True)

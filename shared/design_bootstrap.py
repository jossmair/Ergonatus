"""Use the suite's single visual definition across independently packaged apps."""
import sys,runpy
from shared.catalog import suite_root
from suite_design import install as bundled_install

def install(app):
    path=suite_root()/'suite_design.py'
    if getattr(sys,'frozen',False) and path.is_file():
        runpy.run_path(str(path))['install'](app)
    else:bundled_install(app)

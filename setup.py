from distutils.core import setup
import py2exe

import os
import matplotlib
import zmq.libzmq

setup(windows=[{ "script":"ApogeeSpectrovision.py",
        "icon_resources":[(1,"apogee.ico")]}],
      options={'build': {'build_base': 'P://Engineering//Elec. Engr//Software//ApogeeSpectrovision//build'},
               'py2exe': {'includes': ['zmq.backend.cython'],
                          'excludes': ['zmq.libzmq', '_gtkagg', '_tkagg',
                                       '_agg2', '_cairo', '_cocoaagg',
                                       '_fltagg', '_gtk', '_gtkcairo'],
                          'dll_excludes': ['libzmq.pyd',
                                           'libgdk_pixbuf-2.0-0.dll',
                                           'libgobject-2.0-0.dll',
                                           'libgdk-win32-2.0-0.dll'],
                          'packages': ['matplotlib', 'pytz'],
                          'dist_dir': 'P://Engineering//Elec. Engr//Software//ApogeeSpectrovision//dist'
                          }},
      data_files=(list(matplotlib.get_py2exe_datafiles()) + ["apogee.ico"] ),)
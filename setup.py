from distutils.core import setup
import py2exe
from constants import VERSION
import numpy

import os
import sys
sys.path.append('..')
sys.path.append('C:/Python27/lib/site-packages/numpy/core')
import matplotlib
import zmq.libzmq

my_data_files = []
# add image files
for files in os.listdir(os.path.join(os.getcwd(), 'image_source')):
    f = 'image_source', [os.path.join(os.getcwd(), 'image_source', files)]
    my_data_files.append(f)

setup(windows=[{ "script":"ApogeeSpectrovision.py",
        "icon_resources":[(1,"apogee.ico")],
        "copyright": 'Copyright (c) 2017 Apogee Instruments, Inc.',
        "company_name": "Apogee Instruments, Inc."}],
      options={'build': {'build_base': 'P://Engineering//Elec. Engr//Software' \
                         '//ApogeeSpectrovisionMesa//build'},
               'py2exe': {'includes': ['zmq.backend.cython',
                                       'INI_Configuration', 'Messages'],
                          'excludes': ['zmq.libzmq', '_gtkagg', '_tkagg',
                                       '_agg2', '_cairo', '_cocoaagg',
                                       '_fltagg', '_gtk', '_gtkcairo'],
                          'dll_excludes': ['libzmq.pyd',
                                           'libgdk_pixbuf-2.0-0.dll',
                                           'libgobject-2.0-0.dll',
                                           'libgdk-win32-2.0-0.dll'],
                          'packages': ['matplotlib', 'pytz'],
                          'dist_dir': 'P://Engineering//Elec. Engr//Software' \
                          '//ApogeeSpectrovisionMesa//dist'
                          }},
      version=VERSION,
      name="Apogee Spectrovision",
      description="Software for Apogee SS-100",
      data_files=(list(matplotlib.get_py2exe_datafiles()) + \
                  ["apogee.ico", "libusb-1.0.dll",
                   "libusb-1.0.exp", "libusb-1.0.lib"] + my_data_files ),)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from INI_Configuration import INIMixin


class ASAbstraction(INIMixin):
    def __init__(self):
        ini_defaults = {'device_serial': '',
                        'current_directory': '',
                        'current_file': ''}
        super(ASAbstraction, self).__init__(ini_defaults=ini_defaults)
        self.x_data_range = [340, 820]
        self.y_data = []
        self.last_file_type = ""
        self.current_file_type = ""
        self.connected = False
        self.connected_serials = []
        self.multi_plot_data = []
        self.dark_pixels = []
        self.auto_integrate = True
        # main thread updates these so worker threads don't access gui
        self.average_scans = 1
        self.integ_time = 2000

    @property
    def device_serial(self):
        return self.ini.device_serial

    @device_serial.setter
    def device_serial(self, new_name):
        self.ini.device_serial = new_name

    @property
    def current_directory(self):
        return self.ini.current_directory

    @current_directory.setter
    def current_directory(self, new_dir):
        self.ini.current_directory = new_dir

    @property
    def current_file(self):
        return self.ini.current_file

    @current_file.setter
    def current_file(self, new_file):
        self.ini.current_file = new_file

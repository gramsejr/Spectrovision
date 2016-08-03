from __future__ import unicode_literals
import logging
import os
import platform
import string

from ConfigParser import ConfigParser, NoSectionError, NoOptionError

class Config(object):
    DEFAULT_INI_SECTION = 'Apogee'
    def __init__(self, ini_defaults, name):
        super(Config, self).__setattr__('ini_defaults', ini_defaults)
        super(Config, self).__setattr__('class_name', name)
        self.ensure_ini_path_exists()

    @property
    def ini_file_name(self):
        system = platform.system()
        if system == "Darwin":
            return os.path.join(os.environ['TMPDIR'],
                                self.DEFAULT_INI_SECTION,
                                '%s.ini' % self.class_name)
        elif system == "Windows":
            return os.path.join(os.environ['APPDATA'],
                                self.DEFAULT_INI_SECTION,
                                '%s.ini' % self.class_name)

    def ensure_ini_path_exists(self):
        d = os.path.dirname(self.ini_file_name)
        if not os.path.exists(d):
            os.makedirs(d)

    def __getattr__(self, k):
        try:
            return self.get_config_val(k)
        except (AttributeError, KeyError):
            pass
        if k in self.ini_defaults:
            self.__setattr__(k, self.ini_defaults[k])
            return self.ini_defaults[k]
        raise AttributeError("Doesn't exist in other class nor INI")

    def __setattr__(self, k, v):
        if not k.lower() == k:
            raise Exception("Key must be lower case")
        config = self.get_config()
        config[k] = v
        self.set_config(config)

    def get_config(self):
        cp = ConfigParser()
        cp.read(self.ini_file_name)
        config = {}
        try:
            options = cp.options(self.DEFAULT_INI_SECTION)
        except NoSectionError:
            return config
        for opt in options:
            config_val = cp.get(self.DEFAULT_INI_SECTION, opt).strip()
            config[opt.lower()] = config_val
        return config

    def get_config_val(self, key):
        config = self.get_config()
        return config[key]

    def set_config(self, config):
        cp = ConfigParser()
        cp.add_section(self.DEFAULT_INI_SECTION)
        for k, v in config.items():
            cp.set(self.DEFAULT_INI_SECTION, k, v)
        with open(self.ini_file_name, "w") as f:
            cp.write(f)


class INIMixin(object):
    def __init__(self, *args, **kwargs):
        ini_defaults = {}
        if 'ini_defaults' in kwargs:
            ini_defaults = kwargs.pop('ini_defaults')
        self.ini = Config(ini_defaults, self.__class__.__name__)
        super(INIMixin, self).__init__(*args, **kwargs)

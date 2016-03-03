# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
from time import sleep
from threading import Event

import minimalmodbus as mb

from constants import *


class DeviceCommunicationError(Exception):
    """This exception is thrown whenever there is a problem communicating."""


DARK_REFERENCE = []
EF_DARK_REFERENCE = []
PF_DARK_REFERENCE = []
DARK_INTEG = 1
EF_DARK_INTEG = 1
PF_DARK_INTEG = 1


class Instrument(object):
    def __init__(self, com_port, slave_address):
        self.instrument = mb.Instrument(com_port, slave_address)
        self.instrument.serial.baudrate = 115200
        self.com_port = com_port
        self.slave_address = slave_address
        self.prev_integ = 1
        self.dark_integ = 1
        self.ef_dark_integ = 1
        self.pf_dark_integ = 1
        self.x_data = []
        self.y_data = []
        self.calibration_scan = []
        self.dark_pixels = []
        self.dark_ref_taken = False
        self.dark_integ_list = [DARK_INTEG, EF_DARK_INTEG, PF_DARK_INTEG]
        self.dark_ref_list = [DARK_REFERENCE, EF_DARK_REFERENCE, PF_DARK_REFERENCE]
        self.light_reference = []
        self.auto_integrate = True
        self.avg_scans = 1
        self.update_integ = Event()
        self.update_integ.set()
        self.update_average_scans = Event()
        self.update_average_scans.clear()
        self.change_units = Event()
        self.change_units.set()
        self.device_free = Event()
        self.device_free.set()
        self.name = ''
        self.file_path = ''
        self.ppf_list = []
        self.integ_list = []
        self.max_peak = []

    @property
    def settings(self):
        return self.name, self.com_port, self.slave_address

    @property
    def sensor_type(self):
        if self.x_data[0] == 340:
            return 'VIS'
        return 'NIR'

    def check_connection(self):
        if not self.instrument.serial.isOpen():
            self.instrument.serial.open()
        try:
            status = self.instrument.read_registers(DA_ADDR_STATUS, 2)
        except(IOError, ValueError):
            try:
                self.instrument.serial.close()
                self.instrument.serial.open()
                status = self.instrument.read_registers(DA_ADDR_STATUS, 2)
            except (IOError, ValueError):
                raise DeviceCommunicationError("No response from device")

    def read_registers(self, reg, inc):
        """returns the data from a specified range of a registers given by a
        starting point 'reg', and number of registers, 'inc' as integer values"""
        self.device_free.wait()
        self.device_free.clear()
        for i in range(100):
            try:
                data = self.instrument.read_registers(reg, inc)
                self.device_free.set()
                return data
            except (IOError, ValueError):
                sleep(0.1)
                pass
        self.device_free.set()
        raise DeviceCommunicationError("No response from device")

    def get_reversed_float(self, starting_reg):
        """this method returns a floating point value which starts at the given
        register address and reverses byte order"""
        reg_values = self.read_registers(starting_reg, 2)
        num_one = mb._numToTwoByteString(reg_values[1])
        num_two = mb._numToTwoByteString(reg_values[0])
        return mb._bytestringToFloat(num_one + num_two)

    def write_float(self, reg_addr, f):
        """takes a float, converts to bytestring, reverses byte order, converts to
        values list, writes to register"""
        f_string = mb._floatToBytestring(f)
        # split first two bytes from second two bytes
        f_beg = f_string[0:2]
        f_end = f_string[2:]
        values_list = mb._bytestringToValuelist(f_end + f_beg, 2)
        self.device_free.wait()
        self.device_free.clear()
        for i in range(100):
            try:
                self.instrument.write_registers(reg_addr, values_list)
                self.device_free.set()
                return
            except (IOError, ValueError):
                sleep(0.1)
                pass
        self.device_free.set()
        raise DeviceCommunicationError("No response from device")


    def write_registers(self, starting_reg, values):
        """takes a list of floats, converts to value pairs, and writes to the
        registers beginning at starting_reg"""
        self.device_free.wait()
        self.device_free.clear()
        for i in range(100):
            try:
                self.instrument.write_registers(starting_reg, values)
                self.device_free.set()
                return
            except (IOError, ValueError):
                sleep(0.1)
                pass
        self.device_free.set()
        raise DeviceCommunicationError("No response from device")

    def get_float(self, int_list):
        """takes a values list pair and returns a float (no byte reversal)"""
        num_one = mb._numToTwoByteString(int_list[0])
        num_two = mb._numToTwoByteString(int_list[1])
        return mb._bytestringToFloat(num_one + num_two)

    def get_float_from_list(self, y):
        """converts a list of values lists to float values"""
        return_data = []
        i = 0
        while i < len(y) - 1:
            return_data.append(round(self.get_float([y[i], y[i+1]]), 8))
            i += 2
        return return_data

    def get_values_from_list_of_floats(self, floats):
        """takes a list of floats and returns their value pair equivalents"""
        values_list = []
        i = 0
        while i < len(floats):
            f_str = mb._floatToBytestring(floats[i])
            f_beg = f_str[0:2]
            f_end = f_str[2:]
            value_pair = mb._bytestringToValuelist(f_beg + f_end, 2)
            values_list.extend(value_pair)
            i += 1
        return values_list

    def get_raw_data(self):
        """gets raw data from registers across the whole spectrum"""
        y = []
        start_reg = DA_ADDR_SPECTRUM
        end_reg = int((self.x_data[-1] - self.x_data[0]) * 2 + start_reg)
        inc = 100
        for reg in np.arange(start_reg, end_reg, inc):
            y.extend(self.read_registers(reg, min(inc, end_reg - reg)))
        y.extend(self.read_registers(reg, 2))
        return self.get_float_from_list(y)

    def set_calibration_data(self, data, lock_code):
        """writes the new calibration data to the wavelength registers. The lock
        code specifies wether to save irradiance data or dark scan data."""
        start_reg = DA_ADDR_SPECTRUM
        end_reg = int((self.x_data[-1] - self.x_data[0]) * 2 + start_reg)
        data_index = 0
        data = [float(self.prev_integ)] + data
        values = self.get_values_from_list_of_floats(data)
        self.write_float(DA_ADDR_MFG_MODE, SECRET_UNLOCK_CODE)
        for reg in np.arange(start_reg, end_reg, 2):
            self.write_registers(
                reg, values[data_index:data_index + min(
                    2, len(values) - data_index)])
            data_index += 2
        self.write_registers(end_reg, values[-2:])
        self.write_float(DA_ADDR_MFG_MODE, lock_code)

    def set_bad_pixel_data(self):
        pixel_data = [float(len(self.dark_pixels))] + \
            self.dark_pixels
        pixel_data += [500.0] * (11 - len(pixel_data))
        values = self.get_values_from_list_of_floats(pixel_data)
        self.write_float(DA_ADDR_MFG_MODE, SECRET_UNLOCK_CODE)
        i = 0
        for reg in np.arange(DA_ADDR_SPECTRUM, DA_ADDR_SPECTRUM + len(values), 2):
            self.write_registers(reg, values[reg - 100: reg - 98])
            i += 2
        self.write_float(DA_ADDR_MFG_MODE, LOCK_IN_BAD_PIXELS)

    def clear_dark_pixels(self):
        self.write_float(DA_ADDR_MFG_MODE, SECRET_UNLOCK_CODE)
        self.write_float(DA_ADDR_MFG_MODE, CLEAR_BAD_PIXELS)

    def dark_ref_clear(self):
        self.write_float(DA_ADDR_MFG_MODE, SECRET_UNLOCK_CODE)
        self.write_float(DA_ADDR_MFG_MODE, CLEAR_DARK_REFERENCE)

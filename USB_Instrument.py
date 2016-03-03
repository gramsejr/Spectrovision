# -*- coding: ascii -*-
import gc
import os
import struct
import sys
import time
from math import ceil
from time import sleep
from threading import Event, BoundedSemaphore

import usb.core
import usb.util
import usb.backend.libusb1 as libusb1

from constants import *


class Commands(object):
    def __init__(self):
        pass

    @property
    def HEADER(self):
        """
        HEADER:
        0 Start Bytes[0:1]       Always the same
        1 Protocol Version[2:3]  Always the same
        2 Flags[4:5]             Always the same
        3 Error Number[6:7]      Always the same
        4 Message Type[8:11]     Changes based on STS_CMD
        5 Regarding[12:15]       Always the same
        6 Reserved[16:21]        Always the same
        7 Checksum Type[22]      Always the same (not using checksum)
        8 Immediate Length[23]   Used for small cmds with payload less than 16 bytes
        9 Immediate Data[24:39]  Ditto
        10 Bytes Remaining[40:43] Number of bytes following header (payload and footer)
        """
        return [
            '\xc1\xc0',
            '\x00\x10',
            '\x00\x00',
            '\x00\x00',
            '\x00\x00\x00\x00',
            '\xde\xad\xbe\xef',
            '\x00\x00\x00\x00\x00\x00',
            '\x00',
            '\x00',
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            '\x14\x00\x00\x00'
        ]

    @property
    def FOOTER(self):
        """
        FOOTER:
        Checksum[0:15]
        End Bytes[16:20]
        """
        return [
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            '\xc5\xc4\xc3\xc2'
        ]


class DeviceCommunicationError(Exception):
    """This exception is thrown whenever there is a problem communicating."""


TARGET_HIGH = 16000
TARGET = 14500
TARGET_LOW = 13000
MAX_AUTO_INTEG = 2000000
MIN_AUTO_INTEG = 1000

CONVERSION_FACTOR = 1.0 / (6.02214150e23 * 6.6260930e-34 * 299792458.0 * 1000)

# temperature coefficients
AT = 0.004489071
BT = -0.2657377928
CT = 6.0963287296
DT =  -44.1423212062

STS_CMD = {
    'get_spectrum':      '\x00\x10\x10\x00',
    'set_integ':         '\x10\x00\x11\x00',
    'get_avg_scans':     '\x00\x00\x12\x00',
    'set_avg_scans':     '\x10\x00\x12\x00',
    'get_wavelen_coeff': '\x01\x01\x18\x00',
    'set_wavelen_coeff': '\x11\x01\x18\x00',
    'get_irrad_calib':   '\x01\x20\x18\x00',
    'set_irrad_calib':   '\x11\x20\x18\x00',
    'get_hot_pixels':    '\x00\x60\x18\x00',
    'set_hot_pixels':    '\x10\x60\x18\x00',
    'read_temperature':  '\x01\x00\x40\x00',
    'get_dev_alias':     '\x00\x02\x00\x00',
    'set_dev_alias':     '\x10\x02\x00\x00'
}

ALIAS = '\xc1\xc0\x00\x10\x00\x00\x00\x00\xde\x00\x02\x00\x00\xad\xbe\xef' \
    '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
    '\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
    '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc5\xc4\xc3\xc2'

DARK_REFERENCE = []
EF_DARK_REFERENCE = []
PF_DARK_REFERENCE = []
DARK_INTEG = 1
EF_DARK_INTEG = 1
PF_DARK_INTEG = 1

sts_semaphore = BoundedSemaphore(value=1)

def pull_alias(device):
    try:
        device.read(0x81, 2048)
    except Exception:
        pass
    try:
        device.write(0x1, ALIAS)
    except usb.core.USBError:
        device.set_configuration()
        try:
            device.write(0x1, ALIAS)
        except usb.core.USBError:
            return 'Error Reading From Device'
    alias = device.read(0x81, 64)
    return ''.join([chr(i) for i in alias[24:24+alias[23]]])

def sts_comm(func):
    def func_wrapper(*args, **kwargs):
        sts_semaphore.acquire()
        ret = None
        try:
            ret = func(*args, **kwargs)
        except (usb.core.USBError), data:
            print data
        sts_semaphore.release()
        return ret
    return func_wrapper


class Instrument(object):
    def __init__(self, device):
        self.dev = device
        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        self.endpoint_out = usb.util.find_descriptor(
            intf, custom_match= \
            lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)
        self.endpoint_in = usb.util.find_descriptor(
            intf, custom_match= \
            lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN)
        self.cmd = Commands()
        # kind of redundant but sometimes if the spec has data stored when we
        # try to connect it will throw errors like a mad man so we will reset it
        # every time we try to connect
        try:
            self.read()
        except Exception:
            pass
        self.reset_spec()
        # these events are checked by the thread assigned by this device and
        # cleared after each one has been serviced
        self.update_integ = Event()
        self.update_integ.set()
        self.update_average_scans = Event()
        self.update_average_scans.clear()
        self.change_units = Event()
        self.change_units.set()
        self.prev_integ = 1
        self.dark_integ = 1
        self.prev_temp = 0
        self.dark_ref_taken = False
        self.light_reference = []
        self.dark_reference = []
        self.x_data = []
        self.y_data = []
        self.calibration_scan = []
        self.dark_pixels = []
        self.auto_integration = True
        self.avg_scans = 1
        self.name = self.get_device_alias()
        self.file_path = ''
        self.calib_coeff = []
        self.wavelength_indices = []
        self.irradiance_data = []
        self.irrad_unit = 0
        self.build_wavelength_indices()
        self.get_irradiance_calibration()
        # initialized to 10 ms integration period
        self.set_integration_period(10000)

    def reconnect(self):
        self.dev = usb.core.find(idVendor=0x2457, idProduct=0x4000)
        if self.dev is None:
            raise DeviceCommunicationError("No Spectroradiometers Connected")
        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        self.endpoint_out = usb.util.find_descriptor(
            intf, custom_match= \
            lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)
        self.endpoint_in = usb.util.find_descriptor(
            intf, custom_match= \
            lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN)

    def build_wavelength_indices(self):
        """constructs a list of tuples containing the pixel index and its
        corresponding actual wavelengths. This values are used for interpolation
        in the correct_data method"""
        self.calib_coeff = self.get_calibration_coefficients()
        if self.calib_coeff[0] > 600:
            self.x_data = range(635, 1101)
            self.sensor_type = 'NIR'
        else:
            self.x_data = range(340, 821)
            self.sensor_type = 'VIS'
        i = 0
        for pixel_index in range(1024):
            wavelen = self.pixel_to_wavelength(pixel_index)
            if self.x_data[i] > wavelen:
                continue
            prev = self.pixel_to_wavelength(pixel_index - 1)
            self.wavelength_indices.append(
                (pixel_index, (self.x_data[i] - wavelen) / (prev - wavelen)))
            i += 1
            if i >= len(self.x_data):
                break

    def pixel_to_wavelength(self, pixel):
        """converts a pixel index to it's corresponding wavelengths based on the
        calibration coefficients stored on the Spectroradiometer"""
        return self.calib_coeff[0] + \
               self.calib_coeff[1] * pixel + \
               self.calib_coeff[2] * pixel ** 2 + \
               self.calib_coeff[3] * pixel ** 3

    def get_spectrum(self, rt=False):
        """This function returns the data ready for plotting and/or user
        analysis. Interpolated, AutoIntegrated (if turned on)"""
        print "begin: %s" % sys.getrefcount(None)
        if self.auto_integration:
            i = 0
            while i < 3:
                prev = self.prev_integ
                data = self.get_pixel_data()
                # we will attempt auto integration a max of three times before
                # blissfully continuing on
                self.auto_integrate(data)
                if prev == self.prev_integ:
                    # no change, we are good to go
                    break
                else:
                    i += 1
        else:
            data = self.get_pixel_data()
        if data is not None:
            self.y_data = self.correct_data(data, rt)
        #print "end: %s" % sys.getrefcount(None)
        return self.y_data + [self.prev_integ]

    def auto_integrate(self, pixel_data):
        """This computes the integration period based on recieved values from
        the spec. We do this before any interpolation so we are comparing
        raw digital counts."""
        new_integ = 0
        peak = max(pixel_data)
        num_max_values = sum(i > 16383 for i in pixel_data)
        if peak > TARGET_HIGH:
            if num_max_values >= 600:
                new_integ = 3000;
            elif num_max_values >= 100:
                new_integ = int(self.prev_integ * 0.25)
            else:
                new_integ = int(self.prev_integ * 0.8)
        elif peak < TARGET_LOW and self.prev_integ != MAX_AUTO_INTEG:
            new_integ = self.prev_integ * TARGET/peak
            new_integ = min(new_integ, MAX_AUTO_INTEG)
            if new_integ < MIN_AUTO_INTEG:
                new_integ = MIN_AUTO_INTEG * 4
        if new_integ:
            self.set_integration_period(new_integ)
            self.prev_integ = new_integ

    def correct_data(self, data, rt):
        """Removes the constant 1500 darkscan, interpolates data, applies
        irradiance calibration if it's a calibrated sensor and returns a list
        of corrected data."""
        self.prev_temp = self.get_internal_temp()
        temperature_compensation = AT * self.prev_temp ** 3 + \
            BT * self.prev_temp ** 2 + CT * self.prev_temp + DT
        # constant 1500 darkscan
        data = [x - 1500 - temperature_compensation for x in data]
        # reflectance/transmittance correction
        if rt:
            data = [100 * (data[i] - self.dark_reference[i]) / \
                    max(1,(self.light_reference[i] - self.dark_reference[i]))\
                    for i in range(len(data))]
        # regular dark reference
        elif self.dark_ref_taken:
            data = [data[i] - \
                    (self.dark_reference[i] * self.prev_integ/self.dark_integ) \
                    for i in range(len(data))]
        corrected_data = []
        #interpolate
        for i in range(len(self.x_data)):
            # get predetermined pixel index and mu for interpolation
            pixel_index, mu = self.wavelength_indices[i]
            f = data[pixel_index - 1] * (1 - mu) + data[pixel_index] * mu
            corrected_data.append(f)
        if self.irradiance_data and self.irrad_unit:
            ratio = self.irradiance_data[0]/self.prev_integ
            corrected_data = [corrected_data[i] * self.irradiance_data[i + 1] *\
                              ratio for i in range(len(corrected_data))]
            if self.irrad_unit == 2:
                corrected_data = [corrected_data[i] * self.x_data[i] * CONVERSION_FACTOR \
                                  for i in range(len(corrected_data))]
        return corrected_data

    @sts_comm
    def write(self, msg):
        """Probably don't need a separate function for this but if we want to do
        any error checks, (ensure len(msg) % 64 == zero) before sending out data
        we can do them here."""
        written = self.endpoint_out.write(msg)
        if written:
            return
        else:
            self.reset_spec()
        written = self.endpoint_out.write(msg)
        if not written:
            raise DeviceCommunicationError('Could not write to device, interface be blocked.\nPlease disconnect and reconnect the Spectroradiometer.')

    @sts_comm
    def read(self):
        """Reads and parses data from the spectrometer. Returns only the data
        bits and leaves out the header and footer bytes. This is so that any
        function can send a command and then read a command and get the data
        back that they expect."""
        msg = self.endpoint_in.read(64)
        ret = None
        if msg[23]:
            # we have some immediate data
            ret = msg[24:24+msg[23]]
        remaining = msg[40] + (msg[41] << 8) + (msg[42] << 16) + (msg[43] << 24) - 20
        if remaining:
            remaining = int(ceil(remaining/64.0) * 64) # round remaing to nearest multiple of 64
            msg += self.endpoint_in.read(remaining, self.prev_integ/1000)
            ret = msg[44:-20]
        return ret

    def set_integration_period(self, new_integ):
        """Input is 4 bytes for time in microseconds. Order is LSB, ..., MSB No
        reply. The minimum is 10."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['set_integ']
        msg[8] = '\x04'
        msg[9] = struct.pack('1I', int(new_integ)) + ''.join(['\x00'] * 12)
        msg += self.cmd.FOOTER
        self.write(''.join(msg))
        self.prev_integ = int(new_integ)

    def get_scans_to_avg(self):
        """Gets the number of scans (1-5000) to average together before
        returning the spectrum."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['get_avg_scans']
        msg = msg + self.cmd.FOOTER
        self.write(''.join(msg))
        ret = self.read()
        if ret is not None:
            ret = ret[0] + (ret[1] << 8)
        else:
            raise DeviceCommunicationError("Could not read from device.\n\nTry reconnecting your Spectroradiometer.")
        return ret

    def set_scans_to_avg(self, num_scans):
        """Sets the number of scans to average (1-5000). Argument is an unsigned
        16-bit integer, LSB first. The spectrum response will still be 16 bits
        per pixel. The average will round to the nearest integer, with any exact
        half being rounded up."""
        self.avg_scans = num_scans
        msg = self.cmd.HEADER
        # set cmd
        msg[4] = STS_CMD['set_avg_scans']
        # set immediate data length
        msg[8] = '\x02'
        # split into bytes, LSB first
        num_scans = chr(num_scans & 0xff) + chr((num_scans >> 8) & 0xff)
        # set immediate data
        msg[9] = num_scans + '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        msg = msg + self.cmd.FOOTER
        self.write(''.join(msg))

    def get_pixel_data(self):
        """This returns the intensity of every pixel on the detector as LSB, MSB
        as soon as it is available. There is no payload in the request. The
        reply has 2048 bytes of payload. The pixel intensities are corrected for
        temperature drift and fixed-pattern noise."""
        msg = self.cmd.HEADER
        # set cmd
        msg[4] = STS_CMD['get_spectrum']
        msg = msg + self.cmd.FOOTER
        self.write(''.join(msg))
        sleep(self.prev_integ/1000000.0 + 0.01)
        ret = self.read()
        if ret is None:
            ret = self.read()
            if ret is None:
                raise DeviceCommunicationError("Could not read from device.\n\nTry reconnecting your Spectroradiometer.")
        return [ret[i] + (ret[i+1] << 8) for i in range(0, len(ret), 2)]

    def get_calibration_coefficients(self):
        """Request has 1-byte input data for coefficient index starting with
        wavelength intercept at index 0. Reply has 4-byte float (LSB first).
        This method returns all 4 calibration coefficients."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['get_wavelen_coeff']
        msg[8] = '\x01'
        msg[9] = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        msg = msg + self.cmd.FOOTER
        self.write(''.join(msg))
        coeffs = []
        c = self.read()
        if c is None:
            c = self.read()
            if c is None:
                raise DeviceCommunicationError("Could not read from device.\n\nTry reconnecting your Spectroradiometer.")
        try:
            coeffs.append(struct.unpack('<f', ''.join([chr(i) for i in c]))[0])
        except struct.error:
            try:
                c = self.read()
                coeffs.append(struct.unpack('<f', ''.join([chr(i) for i in c]))[0])
            except Exception, data:
                raise DeviceCommunicationError("Communication Error", "%s" % data)
        msg[9] = '\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.write(''.join(msg))
        c = self.read()
        if c is None:
            c = self.read()
            if c is None:
                raise DeviceCommunicationError("Could not read from device.\n\nTry reconnecting your Spectroradiometer.")
        coeffs.append(struct.unpack('<f', ''.join([chr(i) for i in c]))[0])
        msg[9] = '\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.write(''.join(msg))
        c = self.read()
        if c is None:
            c = self.read()
            if c is None:
                raise DeviceCommunicationError("Could not read from device.\n\nTry reconnecting your Spectroradiometer.")
        coeffs.append(struct.unpack('<f', ''.join([chr(i) for i in c]))[0])
        msg[9] = '\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.write(''.join(msg))
        c = self.read()
        if c is None:
            c = self.read()
            if c is None:
                raise DeviceCommunicationError("Could not read from device.\n\nTry reconnecting your Spectroradiometer.")
        coeffs.append(struct.unpack('<f', ''.join([chr(i) for i in c]))[0])
        return coeffs

    def set_calibration_coefficients(self, new_coeff):
        """Input is the order of the coefficient to set (indexing starts with
        wavelength intercept at index 0), followed by an IEEE single-precision
        float. No reply."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['set_wavelen_coeff']
        msg[8] = '\x05'
        msg[9] = '\x00' + struct.pack('1f', new_coeff[0]) + \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        msg += self.cmd.FOOTER
        self.write(''.join(msg))
        msg[9] = '\x01' + struct.pack('1f', new_coeff[1]) + \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.write(''.join(msg))
        msg[9] = '\x02' + struct.pack('1f', new_coeff[2]) + \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.write(''.join(msg))
        msg[9] = '\x03' + struct.pack('1f', new_coeff[3]) + \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        self.write(''.join(msg))
        self.calib_coeff = new_coeff

    def get_internal_temp(self):
        """Provides the temperature in C (if calibrated) or raw counts for the
        sensor (if uncalibrated). Input is 1 byte for the index of the sensor to
        read. Reply: output is a 4-byte float (LSB first) of temperature in C."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['read_temperature']
        msg[8] = '\x01'
        msg[9] = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        msg += self.cmd.FOOTER
        # since the index we want is zero, we won't change msg[9]
        self.write(''.join(msg))
        temp = self.read()
        return struct.unpack('<f', ''.join([chr(i) for i in temp]))[0]

    def get_irradiance_calibration(self):
        """Request has no payload. Reply has up to 4096 bytes (whatever has been
        stored previously), intended for 1024 x 4-byte floats. If nothing has
        been stored, the reply will have NACK bit set in flags."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['get_irrad_calib']
        msg += self.cmd.FOOTER
        self.write(''.join(msg))
        irrad_data = self.read()
        if irrad_data is None:
            return
        irrad_data = ''.join([chr(i) for i in irrad_data])
        self.irradiance_data = [struct.unpack('<f', j)[0] \
                                for j in [irrad_data[i:i+4]\
                                          for i in range(0, len(irrad_data), 4)]]

    def set_irradiance_calibration(self, calibration_data):
        """Request has up to 4096 bytes in payload. Sending a zero-length buffer
        will delete any irradiance calibration from STS. No reply."""
        # calibration comes in as a list of floats. need to convert to char
        # array before sending data
        calibration_data = ''.join(
            [struct.pack('1f', ratio) for ratio in calibration_data])
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['set_irrad_calib']
        length = 20 + len(calibration_data)
        msg[10] = struct.pack('1I', length)
        msg += calibration_data
        msg += self.cmd.FOOTER
        self.write(msg)

    def get_device_alias(self):
        """User-defined name for the device (e.g., station number)"""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['get_dev_alias']
        msg += self.cmd.FOOTER
        self.write(''.join(msg))
        alias = self.read()
        if alias is None:
            alias = 'None'
        else:
            alias = ''.join([chr(i) for i in alias])
        return alias

    def set_device_alias(self, new_name):
        """If string length is 0, alias will be deleted"""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['set_dev_alias']
        msg[8] = chr(len(new_name))
        msg[9] = str(new_name) + ''.join(['\x00'] * (16 - len(new_name)))
        msg += self.cmd.FOOTER
        self.write(''.join(msg))

    def get_hot_pixel_indices(self):
        """Request has no data. Reply has up to 58 x 2-byte integers (1 integer
        per pixel index). If nothing has been stored, the reply will have NACK
        bit set in flags."""
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['get_hot_pixels']
        msg += self.cmd.FOOTER
        ret = self.read()
        if ret is None:
            ret = self.read()
            if ret is None:
                return
        self.dark_pixels = [ret[i] + (ret[i+1] << 8) for i in range(0, len(ret), 2)]

    def set_hot_pixel_indices(self, new_indices):
        """Request has up to 58 x 2-byte integers for pixel indices. No reply."""
        new_indices = ''.join([struct.pack('1h', new_indices[i]) for i in range(len(new_indices))])
        msg = self.cmd.HEADER
        msg[4] = STS_CMD['set_hot_pixels']
        if len(new_indices <= 16):
            msg[8] = chr(len(new_indices))
            msg[9] = new_indices + ''.join(['\x00'] * (16 - len(new_indices)))
        else:
            msg[10] = struct.pack('1I', len(new_indices) + 20)
            msg += new_indices
        msg += self.cmd.FOOTER
        self.write(''.join(msg))

    def reset_spec(self):
        """Forces a reset of the device. Wait 1 second before reopening the
        port."""
        return
        msg = self.cmd.HEADER + self.cmd.FOOTER
        self.write(''.join(msg))
        sleep(1)
        self.reconnect()

    def disconnect_spec(self):
        try:
            #msg = self.cmd.HEADER + self.cmd.FOOTER
            #self.write(''.join(msg))
            #sleep(1)
            usb.util.release_interface(self.dev, 0)
            usb.util.dispose_resources(self.dev)
        except Exception, data:
            pass

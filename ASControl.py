# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import gc
import itertools
import multiprocessing
import os
import sys
import time
import urllib2
from Queue import Queue, Empty
from tempfile import gettempdir
from threading import Event, Thread
from time import sleep

from serial.tools.list_ports import comports
import usb.util
import usb.core
import usb.backend.libusb1
if sys.platform != 'darwin':
    backend = usb.backend.libusb1.get_backend(
        find_library=lambda x: (os.path.join(os.getcwd(), 'libusb-1.0.dll')))
else:
    backend = usb.backend.libusb1.get_backend(
        find_library=lambda x: (os.path.join(os.getcwd(), 'libusb-1.0.dylib')))

import wx
import wx.lib.newevent
from wx import PostEvent, Yield

from constants import *
from USB_Instrument import Instrument, DeviceCommunicationError, ALIAS, AT, BT, CT

event_error, EVT_ERROR = wx.lib.newevent.NewEvent()
plot_event, PLOT_EVT = wx.lib.newevent.NewEvent()
status_event, STATUS_EVT = wx.lib.newevent.NewEvent()
toolbar_event, TOOLBAR_EVT = wx.lib.newevent.NewEvent()


class InvalidCommandError(Exception):
    """This exception is thrown when the command cannot be carried out for
    various reasons"""


class ASControl(object):
    def __init__(self, abstraction, interaction, presentation):
        self.abstr = abstraction
        self.prsnt = presentation
        self.data_capture_queue = Queue()
        self.plot_data_queue = Queue()
        self.start_thread = Event()
        self.start_thread.clear()
        self.stop_thread = Event()
        self.pause_thread = Event()
        self.hold_thread = Event()
        self.devices = []
        self.active_threads = []
        self.data_collection = False
        interaction.install(self, presentation)
        self.red_farred = ([635, 685], [710,760])
        self.active_mode = COUNTS
        self.check_for_updates()

    @property
    def active_device(self):
        dev_name = self.prsnt.active_device
        if not dev_name:
            msg = "Please connect a device before attempting this function."
            evt = event_error(title="No Device Selected", msg=msg)
            PostEvent(self.prsnt.frame, evt)
            return
        for device in self.devices:
            if device.name == dev_name:
                return device

    def plot_from_file(self, file_paths=[]):
        """
        parses file of csv format and plots each line as a seperate measurement
        uses the timestamp as a label for the legend. only accomadates a max of
        ten seperate plots as we don't know how much memory the system using the
        software is going to have
        """
        if not file_paths:
            file_paths = self.prsnt.open_data_file_dialog(
                self.abstr.current_directory)
            if not file_paths:
                return
        # update directory and file for persistence purposes
        self.abstr.current_directory = os.path.dirname(file_paths[0])
        self.abstr.current_file = os.path.basename(file_paths[0])
        file_contents = []
        total_plots = 0
        temperature = False
        for file_path in file_paths:
            dictionary = {}
            dictionary['labels'] = []
            with open(file_path, 'r') as data_file:
                file_string = data_file.read()
            lines_in_file = file_string.split('\n')
            try:
                lines_in_file.remove('')
            except ValueError:
                pass
            rows = []
            for line in lines_in_file:
                line = line.split(',')
                rows.append(line)
            data = list(itertools.izip_longest(*rows))
            x_data = list(data[0][2:-8])
            while True:
                try:
                    x_data.remove('-')
                except ValueError:
                    break
            dictionary['x_data'] = map(lambda x: float(x), x_data)
            dictionary['y_data'] = []
            j = 1
            while j < len(data):
                elements = list(data[j])
                elements = ['0' if i == '-' else i for i in elements]
                # if elements[0] == timestamp, then we have encountered a file
                # with data from two different sensors. start a new dictionary
                # as if the following data was from a seperate file
                if elements[0] == 'Timestamp':
                    file_contents.append(dictionary)
                    dictionary = {}
                    dictionary['labels'] = []
                    dictionary['x_data'] = map(lambda x: float(x),
                                               elements[2:-8])
                    dictionary['y_data'] = []
                    j += 1
                    elements = data[j]
                dictionary['labels'].append(elements[0])
                y_data = list(elements[2:-1]) # exclude temperature
                try:
                    y_data.remove('')
                except ValueError:
                    pass
                while True:
                    try:
                        y_data.remove('-')
                    except ValueError:
                        break
                dictionary['y_data'].append(map(lambda y: float(y), y_data))
                j += 1
                total_plots += 1
                if total_plots == 10:
                    break
            file_contents.append(dictionary)
            if total_plots == 10:
                break
        self.abstr.y_data = []
        self.abstr.multi_plot_data = file_contents
        self.prsnt.show_average_button.Enable()
        self.prsnt.plot_multiline(file_contents)

    def save_spectrum(self):
        """
        saves the current spectrum as an image file with filetype of the users
        choice
        """
        file_path = self.prsnt.save_spectrum_dialog(
            self.abstr.current_directory,
            os.path.splitext(self.abstr.current_file)[0])
        if not file_path:
            return
        self.abstr.current_file = os.path.basename(file_path)
        self.abstr.current_directory = os.path.dirname(file_path)
        self.prsnt.save_graph(file_path)

    def setup_data_capture(self):
        """
        intializes/prompts user for data capture settings and begins data
        capture threads. If user entered a start time, this method will wait
        until specified time before starting threads. DISCLAIMER: timing may
        not be exact.
        """
        self.stop_all_threads()
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        settings = self.prsnt.data_capture_settings_dlg()
        if not settings:
            return
        cont = True
        # get a filepath for each device connected
        for device in self.devices:
            if self.prsnt.active_mode == RT:
                if not (device.dark_ref_list[0] and device.light_reference):
                    msg = "Please take a Dark and Light Reference point for %s" \
                    "\n before attempting to plot Reflectance/Transmittance"
                    self.prsnt.give_error("No Light/Dark Reference",
                                                 msg % device.name)
                    cont = False
                    continue
            suggested_name = device.name
            file_path = ''
            if settings['save_to_file']:
                file_path = self.prsnt.save_data_dialog(
                    self.abstr.current_directory, suggested_name)
                if not file_path:
                    msg = "Could not retrieve a file name. Do you want to " \
                        "proceed without saving data for device %s?" 
                    title = "No Filepath Given"
                    proceed = self.prsnt.ok_cancel(title,
                                                          msg % device.name)
                    if not proceed:
                        return
            if not file_path:
                file_path = os.path.join(gettempdir(), '%s.csv' % device.name)
                # remove temp file if it exists to prevent appending onto old
                # irrelevant data
                if os.path.exists(file_path):
                    os.remove(file_path)
            device.file_path = file_path
            try:
                if self.abstr.auto_integrate:
                    device.auto_integration = True
                else:
                    device.auto_integration = False
                    device.set_integration_period(self.prsnt.integ_time)
                device.set_scans_to_avg(int(self.prsnt.average_scans))
            except DeviceCommunicationError, data:
                self.prsnt.give_error("Connection Error %s" % device.name,
                                             data.message)
        if not cont:
            return
        self.abstr.multi_plot_data = []
        if settings['start_time']:
            start_time = settings['start_time']
            dlg = self.prsnt.gen_prog_dlg(
                "Data Capture Countdown",
                "Your data capture application will start at: \n %s"
                % settings['start_time'].strftime("%H:%M:%S"), 0)
            t = -1
            while t < 0:
                t = (datetime.datetime.now() - start_time).total_seconds()
                cont, skip = dlg.Pulse()
                if not cont:
                    dlg.Close()
                    dlg.Destroy()
                    return
                sleep(0.005)
            dlg.Close()
            dlg.Destroy()
        proceed = self.prsnt.progress_dialog(
            settings, self.collect_raw_data)
        if not proceed:
            self.stop_thread.set()
        if settings['plot_to_screen']:
            plot_files = []
            for device in self.devices:
                plot_files.append(device.file_path)
            self.plot_from_file(plot_files)

    def collect_raw_data(self, total_scans, time_between_scans, log_temp,
                         active_mode=0, active_unit=0):
        """
        collects data during data capture process and writes it to a file after
        each scan. if no file is chosen, data is written to a temp file. This
        function is a generator for the progress dialog.
        """
        self.data_collection = True
        scan_data = []
        self.abstr.y_data = []
        # float("inf") wasn't working correctly for XP users
        # 8000000 gives roughly 40 GB of data per sensor.
        # Should be sufficient yah?
        if total_scans == 0:
            total_scans = 8000000
        i = 1
        if not time_between_scans:
            time_between_scans = 0
        # if total scans is infinite, data collection will proceed until user
        # hits cancel on the generator controlled progress dialog. the dialog
        # sets the self.stop_thread Event which is checked here before every
        # scan
        while i < total_scans+1:
            wx.YieldIfNeeded()
            scan_time = time.time()
            # now collect the data from the devices and save them to their 
            # respective files
            for dev in self.devices:
                dev.start_measurement()
            wx.YieldIfNeeded()
            inc = (self.devices[0].prev_integ/1000000.0*self.devices[0].avg_scans + 0.01)/10
            for i in range(10):
                sleep(inc)
                wx.YieldIfNeeded()
            for dev in self.devices:
                yield i
                try:
                    dev.acquire_measurement()
                    wx.YieldIfNeeded()
                except DeviceCommunicationError, data:
                    print data
                else:
                    y = dev.y_data
                if active_mode in [ENERGY_FLUX, ILLUMINANCE]:
                    y = self.integrate_range(dev.x_data, y)
                elif active_mode == PHOTON_FLUX:
                    y = self.calculate_ypf(dev.x_data, y)
                elif active_unit == LUX:
                    y = self.calculate_lux(y, dev.x_data)
                elif active_unit == FOOTCANDLE:
                    y = self.calculate_lux(y, dev.x_data, fc=True)
                self.abstr.y_data = [y]
                temp = None
                if log_temp:
                    temp = dev.prev_temp
                wx.YieldIfNeeded()
                self.save_data_to_file(dev.file_path, 'r+',
                                       [dev.x_data[0], dev.x_data[-1]],
                                       temp, active_mode, active_unit)
            # if there is a time_between_scans parameter, make sure we hit that
            # point before continuing. otherwise, time_between_scans is roughly
            # the amount of time it takes to pull the data off the registers
            # and save it to the file
            while time.time() - time_between_scans < scan_time:
                try:
                    wx.Yield()
                except Exception:
                    # this exception is a wx._core.PyAssertionError which for some
                    # reason I can't explicitly catch so I'm using a catch all here.
                    # this error is raised when wx.Yield is called recursively
                    pass
                if (i) == total_scans:
                    break
                sleep(0.01)
                yield i
            i += 1
        self.data_collection = False

    def save_data_to_file(self, file_path='', mode='r+', x_data=[],
                          sensor_temp=None, active_mode=-1, active_unit=-1):
        """
        takes the data of the current graph and saves it to a file. If the
        file exists and append=True, data is appended to end of file
        if the file is already open it cannot be written too. in this case
        the data is simply thrown away
        """
        if not (self.abstr.y_data or self.abstr.multi_plot_data):
            msg = "Please take a reading before attempting this function."
            self.prsnt.give_error("No Scan Data", msg)
            return
        if not file_path:
            file_path = self.prsnt.save_data_dialog(
                self.abstr.current_directory,
                os.path.splitext(self.abstr.current_file)[0])
            if not file_path:
                return
        # determine if path exists and update current file and directory in ini
        path_exists = os.path.exists(file_path)
        self.abstr.current_directory = os.path.dirname(file_path)
        self.abstr.current_file = os.path.basename(file_path)
        content = []
        # determine mode and unit to determine what data needs to be written to
        # file
        if active_mode < 0:
            active_mode = self.prsnt.active_mode
        if active_unit < 0:
            active_unit = self.prsnt.active_unit
        # create single plot data
        if not self.abstr.multi_plot_data:
            # file type is used to determine whether or not we need to write a
            # column of wavelength values or not. only relevant for single plot
            # data.
            if self.abstr.y_data[0] is None:
                return
            self.abstr.current_file_type = self.devices[0].sensor_type
            non_matching = self.abstr.current_file_type != \
                self.abstr.last_file_type
            column1 = []
            if not path_exists or non_matching:
                column1 = ['Timestamp', 'Units'] + self.devices[0].x_data
                column1 += ['-'] * (483-len(column1))
                column1 += ['Integration Time (ms)','Integrated Total', 'PPF',
                            'YPF', 'PPE', 'Fraction of Total', 'R/FR', 'Sensor Temp']
                if not non_matching:
                    mode = 'w'
            content = ['%s %s' % (
                datetime.datetime.now().strftime("%H:%M:%S %Y/%m/%d"),
                self.devices[0].name), MODE_TO_UNITS[active_mode]]
            if self.abstr.current_file_type == 'NIR':
                content += self.abstr.y_data[0][:466] + ['-'] * 15 + \
                    self.abstr.y_data[0][466:]
            else:
                content += self.abstr.y_data[0]
            if active_mode == ENERGY_FLUX:
                content.insert(-2, '-')
                content.insert(-2, '-')
                content.insert(-2, '-')
            elif active_mode == ILLUMINANCE:
                content.insert(-1, '-')
                content.insert(-1, '-')
                content.insert(-1, '-')
            content += ["-"] * (491 - len(content))
            if sensor_temp is not None:
                content[-1] = sensor_temp
            if active_mode == 4: #lux or fc
                content[1] = content[1] % UNITS_TO_STR[active_unit]
            if column1:
                content = ["%s,%s" % (column1[i], content[i])
                           for i in range(len(column1))]
        # create multiplot data
        else:
            content = [""] * 491
            for scan_data in self.abstr.multi_plot_data:
                new_col = ['Timestamp', 'Units'] + list(scan_data['x_data'])
                new_col += ['-'] * (483 - len(new_col))
                new_col += ['Integration Time (ms)', 'Integrated Total', 'PPF',
                           'YPF', 'PPE', 'Fraction of Total', 'R/FR', 'Sensor Temp']
                i = 0
                if content[0]:
                    content = ["%s,%s" % (content[i], new_col[i])
                               for i in range(491)]
                else:
                    content = ["%s" % new_col[i] for i in range(491)]
                for y_data in scan_data['y_data']:
                    new_col =['%s %s' % (
                        datetime.datetime.now().strftime("%H:%M:%S %Y/%m/%d"),
                        scan_data['labels'][0]), MODE_TO_UNITS[active_mode]]
                    if len(y_data) < 480:
                        new_col += y_data[:466] + ['-'] * 15 + y_data[466:]
                    else:
                        new_col += y_data
                    if active_mode == ENERGY_FLUX:
                        new_col.insert(-2, '-')
                        new_col.insert(-2, '-')
                        new_col.insert(-2, '-')
                    elif active_mode == ILLUMINANCE:
                        new_col.insert(-1, '-')
                        new_col.insert(-1, '-')
                        new_col.insert(-1, '-')
                    new_col += ["-"] * (491 - len(new_col))
                    if active_mode == 4:
                        new_col[1] = new_col[1] % UNITS_TO_STR[active_unit]
                    content = ["%s,%s" % (content[i], new_col[i])
                               for i in range(491)]
                    i += 1
        try:
            if mode == 'r+' and path_exists:
                # this means we are appending a new column onto preexisting data
                prev_content = []
                # read in file content
                with open(file_path, 'r') as data_file:
                    file_content = data_file.read()
                file_content = file_content.split('\n')
                # remove any empty fields
                try:
                    file_content.remove("")
                except Exception:
                    pass
                file_content = ["%s,%s" % (file_content[i], content[i])
                                for i in range(491)]
            else:
                file_content = content
            with open(file_path + '_Backup', 'w') as data_file:
                data_file.write("\n".join(file_content))
            with open(file_path, 'w') as data_file:
                data_file.write("\n".join(file_content))
            os.remove(file_path + "_Backup")
        except IOError, data:
            if not self.data_collection:
                evt = event_error(title="File IO Error",
                                  msg="Could not open file %s\n\n Make sure its " \
                                  "not open somewhere and try again." % file_path)
                PostEvent(self.prsnt.frame, evt)
        else:
            self.abstr.last_file_type = self.abstr.current_file_type

    def connect_to_device(self):
        """connects to device, updates the spectrum, sets wavelength for the
        device, and updates prsnt to reflect new settings"""
        self.stop_all_threads()
        possible = usb.core.find(find_all=True,
                                 idVendor=0x2457,
                                 idProduct=0x4000,
                                 backend=backend)
        possible = [dev for dev in possible]
        if not possible:
            self.prsnt.give_error(
                'Device Not Connected',
                'There is no spectroradiometer connected to the Mesa.')
            return
        devices = []
        #sleep(0.5)
        for dev in possible:
            try:
                dev.set_configuration()
                cfg = dev.get_active_configuration()
                intf = cfg[(0, 0)]
                endpoint_out = usb.util.find_descriptor(
                    intf, custom_match= \
                    lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_OUT)
                endpoint_in = usb.util.find_descriptor(
                    intf, custom_match= \
                    lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_IN)
                try:
                    try:
                        # flush buffer of any previous data
                        endpoint_in.read(3000, 10)
                    except usb.core.USBError:
                        pass
                    endpoint_out.write(ALIAS)
                    response = endpoint_in.read(64)
                    try:
                        device_alias = ''.join([chr(i) for i in \
                                                response[24:24+response[23]]])
                    except UnicodeDecodeError:
                        # clear garbage from buffer and try again
                        try:
                            endpoint_in.read(3000, 10)
                        except usb.core.USBError:
                            pass
                        endpoint_out.write(ALIAS)
                        response = endpoint_in.read(64)
                        device_alias = ''.join([chr(i) for i in \
                                                response[24:24+response[23]]])
                    if device_alias or device_alias == '':
                        devices.append((dev, device_alias))
                except usb.core.USBError, data:
                    print data
                finally:
                    usb.util.release_interface(dev, 0)
                    usb.util.dispose_resources(dev)
            except (usb.core.USBError, NotImplementedError), data:
                print data
        for a in devices:
            if a[1] in self.abstr.connected_devices:
                devices.remove(a)
        if len(devices) == 1:
            try:
                self.devices.append(Instrument(devices[0][0]))
                alias = devices[0][1]
            except usb.core.USBError, data:
                print data
        elif devices:
            alias = self.prsnt.connection_settings_query(
                self.abstr.device_alias, [a[1] for a in devices])
            if alias is None:
                return
            self.abstr.device_alias = alias
            for a in devices:
                try:
                    if a[1] == alias:
                        self.devices.append(Instrument(a[0]))
                        break
                except Exception:
                    pass
        else:
            self.prsnt.give_error(
                'Device Not Connected',
                'There is no spectroradiometer connected to this computer.')
            return
        self.abstr.connected_devices.append(alias)
        device = self.devices[-1]
        self.abstr.x_data_range = [device.x_data[0], device.x_data[-1]]
        self.prsnt.x_axis_limits = (device.x_data[0], device.x_data[-1])
        self.prsnt.x_data = device.x_data
        self.abstr.connected = True
        self.prsnt.enable_disconnect()
        self.prsnt.add_sensor_to_toolbar(device.name, self.right_click_menu)
        return

    def disconnect_device(self):
        """disconnects a device from the application. if no other devices are
        connected, application returns to a not connected state"""
        current_devices = []
        self.stop_all_threads()
        for device in self.devices:
            current_devices.append(device.name)
        if not current_devices:
            return
        device_to_disconnect = self.prsnt.disconnect_dialog(
            current_devices)
        if not device_to_disconnect:
            return
        dev = [i for i in self.devices if i.name == device_to_disconnect][0]
        self.disconnect(dev)
        self.prsnt.confirmation_message("Device has been disconnected.",
                                               "Success!")

    def disconnect(self, dev):
        self.stop_all_threads()
        paired = None
        if dev.paired:
            self.prsnt.remove_pair((dev.name, dev.paired))
            paired = dev.paired
        dev.disconnect_spec()
        self.prsnt.remove_device(dev.name)
        self.devices.remove(dev)
        try:
            self.abstr.connected_devices.remove(dev.name)
        except ValueError: # not in list
            pass
        if not self.devices:
            self.abstr.connected = False
            self.prsnt.enable_disconnect(False)
        if len(self.devices) == 1:
            self.prsnt.x_data = self.devices[0].x_data
        if paired is not None:
            for dev in self.devices:
                if dev.name == paired:
                    dev.paired = False
        while not self.plot_data_queue.empty():
            self.plot_data_queue.get()
        if len(self.devices) == 1:
            self.prsnt.x_data = self.devices[0].x_data

    def start_plot_threads(self):
        """initalizes startup settings, starts a thread to carry out
        plotting and a seperate thread to carry out data retrieval"""
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        self.stop_thread.clear()
        self.pause_thread.clear()
        self.hold_thread.clear()
        evt = status_event(status="Plotting Continuous Reading")
        PostEvent(self.prsnt.frame, evt)
        evt = toolbar_event(enable=False)
        PostEvent(self.prsnt.frame, evt)
        self.prsnt.show_average_button.SetValue(False)
        self.prsnt.color_map.Disable()
        if self.start_thread.is_set():
            return
        self.start_thread.set()
        for device in self.devices:
            device.change_units.set()
        self.abstr.multi_plot_data = {}
        plot_thread = Thread(target=self.plot_data, name="Plot Thread")
        plot_thread.start()
        self.active_threads.append(plot_thread)
        for device in self.devices:
            thread = Thread(target=self.retrieve_data,
                            kwargs={'device': device},
                            name="Data Retrieval Thread %s"
                            % device.name[-1])
            thread.start()
            self.active_threads.append(thread)

    def plot_data(self):
        """waits for plot data to be thrown on a thread safe queue by the data
        retrieval thread and plots it. data comes in as a tuple of the form
        (y_data, label, x_data)"""
        multiplot = False
        if len(self.devices) > 1:
            multiplot = True
            plot_data = []
        while not self.plot_data_queue.empty():
            self.plot_data_queue.get()
        while not self.stop_thread.is_set():
            if not self.devices:
                return
            try:
                for dev in self.devices:
                    if not dev.data_ready.is_set():
                        raise Exception("Data not ready")
            except Exception:
                sleep(0.1)
            else:
                if multiplot:
                    for dev in self.devices:
                        scan = {}
                        scan['y_data'] = [dev.y_data]
                        scan['labels'] = [dev.name]
                        scan['x_data'] = dev.x_data
                        dev.data_ready.clear()
                        plot_data.append(scan)
                    if len(plot_data) == len(self.devices):
                        # sort the scans according to label/device.name so they
                        # are the same color from plot to plot and in the same
                        # position in the legend. legend position is used to 
                        # determine which data belongs to the active device
                        # in calibrated modes to display integrated totals
                        plot_data = sorted(plot_data,
                                           key=lambda scan: scan['labels'][0])
                        paired = []
                        for dev in self.devices:
                            if dev.paired:
                                already_paired = False
                                for p in paired:
                                    if dev.name in p:
                                        already_paired = True
                                if not already_paired:
                                    paired.append((dev.name, dev.paired))
                        evt = plot_event(multiline=True,
                                         plot_data=plot_data,
                                         average=False,
                                         active_device=self.active_device.name,
                                         paired=paired)
                        try:
                            PostEvent(self.prsnt.frame, evt)
                        except Exception:
                            pass
                        self.abstr.multi_plot_data = plot_data
                        plot_data = []
                else:
                    evt = plot_event(plot_data=self.devices[0].y_data,
                                     label=self.devices[0].name)
                    self.devices[0].data_ready.clear()
                    try:
                        PostEvent(self.prsnt.frame, evt)
                    except Exception:
                        pass

    def retrieve_data(self, device):
        """the intent is that the data retrieval thread stays in this loop while
        taking continuous readings"""
        while not self.stop_thread.is_set():
            while (self.pause_thread.is_set()):
                evt = toolbar_event(enable=True)
                try:
                    PostEvent(self.prsnt.frame, evt)
                except Exception:
                    pass
                if self.stop_thread.is_set():
                    try:
                        evt = toolbar_event(enable=True)
                        PostEvent(self.prsnt.frame, evt)
                        evt = status_event(status="")
                        PostEvent(self.prsnt.frame, evt)
                    except Exception:
                        pass
                    return
                sleep(0.005)
            try:
                while device.data_ready.is_set():
                    sleep(0.05)
                self.get_active_signal_data(device)
            except DeviceCommunicationError, data:
                evt = event_error(title="Connection Error", msg=data.message)
                PostEvent(self.prsnt.frame, evt)
                self.stop_all_threads()
            except InvalidCommandError:
                self.stop_all_threads()
            else:
                self.abstr.y_data = [device.y_data]
                if self.active_device.name == device.name:
                    evt = status_event(integ_time=device.prev_integ)
                    try:
                        PostEvent(self.prsnt.frame, evt)
                    except Exception:
                        pass
        try:
            evt = toolbar_event(enable=True)
            PostEvent(self.prsnt.frame, evt)
            evt = status_event(status="")
            PostEvent(self.prsnt.frame, evt)
        except Exception:
            pass

    def get_active_signal_data(self, device):
        """determines which plot mode is active and returns the data
        accordingly"""
        active_mode = self.prsnt.active_mode
        if device.update_integ.is_set():
            device.auto_integration = self.abstr.auto_integrate
            if not device.auto_integration:
                device.set_integration_period(self.abstr.integ_time)
            device.update_integ.clear()
        if device.update_average_scans.is_set():
            device.set_scans_to_avg(self.abstr.average_scans)
            device.update_average_scans.clear()
        if active_mode == RELATIVE:
            self.get_relative_signal(device)
        elif active_mode == RT:
            if not (device.dark_reference and device.light_reference):
                msg = "Please take a Dark and Light Reference point for %s" \
                    "\n before attempting to plot Reflectance/Transmittance"
                self.prsnt.give_error("No Light/Dark Reference",
                                             msg % device.name)
                raise InvalidCommandError
            self.get_reflectance_transmittance(device)
        else:
            self.get_irradiance(device)

    def get_relative_signal(self, device):
        """returns the raw singal as digital counts"""
        if device.change_units.is_set():
            device.irrad_unit = COUNTS
            device.change_units.clear()
            self.prsnt.label = r'Counts'
        device.get_spectrum()

    def get_irradiance(self, device):
        """returns irradiance signal in either micromol or W/m^2"""
        active_mode = self.prsnt.active_mode
        active_unit = self.prsnt.active_unit
        if device.change_units.is_set():
            if active_mode == ENERGY_FLUX or active_mode == ILLUMINANCE:
                device.irrad_unit = WATTS_PER_METER_SQUARED
                if active_unit == LUX:
                    self.prsnt.label = LUX_LABEL
                elif active_unit == FOOTCANDLE:
                    self.prsnt.label = FC_LABEL
                else:
                    self.prsnt.label = WM2_LABEL
            elif active_mode == PHOTON_FLUX:
                device.irrad_unit = MICRO_MOLES
                self.prsnt.label = MICROMOL_LABEL
            device.change_units.clear()
        device.start_measurement()
        inc = (device.prev_integ/1000000.0 * device.avg_scans + 0.01)/10
        for i in range(10):
            sleep(inc)
            wx.YieldIfNeeded()
        device.acquire_measurement()
        if active_unit == LUX:
            device.y_data = self.calculate_lux(device.y_data, device.x_data)
        elif active_unit == FOOTCANDLE:
            device.y_data = self.calculate_lux(device.y_data, device.x_data,
                                               fc=True)
        if active_mode in [ENERGY_FLUX, ILLUMINANCE]:
            device.y_data = self.integrate_range(device.x_data, device.y_data)
        if active_mode == ILLUMINANCE:
            del device.y_data[-2:]
        elif active_mode == PHOTON_FLUX:
            device.y_data = self.calculate_ypf(device.x_data, device.y_data)
        device.data_ready.set()

    def integrate_range(self, x_range, y):
        """calculates an integrated total"""
        total = fraction = i = r = fr = 0
        integ_range = self.prsnt.integ_lines
        fractional_range = self.prsnt.fractional_lines
        red, far_red = RED_FARRED
        for x in x_range:
            if integ_range[0] <= x <= integ_range[1]:
                total += y[i]
            if fractional_range[0] <= x <= fractional_range[1]:
                fraction += y[i]
            if red[0] <= x <= red[1]:
                r += y[i]
            if far_red[0] <= x <= far_red[1]:
                fr += y[i]
            i += 1
        return y + [total, fraction/total, r/fr]

    def calculate_ypf(self, x_range, y):
        """calculates an integrated total, ypf, ppf, and ppe, fraction/total"""
        if not y:
            return
        total = fraction = ypf = ppf = ppe_r = ppe_fr = i = r = fr = 0
        integ_range = self.prsnt.integ_lines
        fractional_range = self.prsnt.fractional_lines
        red, far_red = RED_FARRED
        for x in x_range:
            x = int(x)
            yp = 0
            if 300 <= x <= 800:
                yp = y[i] * RQE[x - 300]
                ypf += yp
                ppe_r += y[i] * SIGMA_R[x - 300]
                ppe_fr += y[i] * SIGMA_FR[x - 300]
            if 400 <= x <= 700:
                ppf += y[i]
            if integ_range[0] <= x <= integ_range[1]:
                total += y[i]
            if fractional_range[0] <= x <= fractional_range[1]:
                fraction += y[i]
            if red[0] <= x <= red[1]:
                r += y[i]
            if far_red[0] <= x <= far_red[1]:
                fr += y[i]
            i += 1
        if ppe_r:
            ppe = ppe_r/(ppe_r + ppe_fr)
        else:
            ppe = 0.0
        if total == 0:
            total = 1 # avoid division by zero
        return y + [total, ppf, ypf, ppe, fraction/total, r/fr]

    def calculate_lux(self, data, x_data, fc = False):
        if not data: return
        y = []
        i = 0
        j = 0
        for x in x_data:
            y.append(0)
            if 380 <= x <= 780:
                y[-1] = LUX_MULTIPLIER * data[i] * CIE_1931[int(x) - 380]
                if fc:
                    y[-1] = y[-1] * LUX_TO_FOOTCANDLES
            i += 1
        return y + data[-1:]

    def get_reflectance_transmittance(self, device):
        """plots reflactance/transmittance as a percentage"""
        if device.change_units.is_set():
            device.irrad_unit = COUNTS
            device.change_units.clear()
            self.prsnt.label = r'Reflectance/Transmittance [$\%$]'
        device.get_spectrum(rt=True)

    def calculate_r_t(self, data, device):
        """calculates the reflectance/transmittance percentage based on the
        saved dark and light reference"""
        transmitted = []
        i = 0
        for point in data:
            dr = device.dark_ref_list[0][i]
            lr = device.light_reference[i]
            if lr - dr == 0:
                lr += 0.00001
            transmitted.append(100 * ((point - dr) / (lr - dr)))
            i += 1
        return transmitted

    def show_help_menu(self, tab):
        self.prsnt.show_help_menu(tab)

    def set_dark_reference(self):
        """save a dark reference to attempt to cancel dark noise or for use with
        reflectance/transmittance"""
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        cont_play = False
        if self.active_threads:
            cont_play = True
        device = self.active_device
        if not device:
            return
        msg = "Cover the sensor head to block all incident radiation, then\n" \
            " press 'OK' to save the dark reference."
        proceed = self.prsnt.ok_cancel("Dark Reference", msg)
        if not proceed:
            return
        busy = self.prsnt.busy("Taking Dark Reference Scan")
        try:
            data = device.get_pixel_data()
            temp = device.get_internal_temp()
            temperature_compensation = AT * temp ** 3 + \
                BT * temp ** 2 + CT * temp
            device.dark_reference = [i - 1500 - temperature_compensation for i in data]
            device.dark_integ = device.prev_integ
        except DeviceCommunicationError, data:
            busy.Destroy()
            wx.YieldIfNeeded()
            del(busy)
            evt = event_error(title="Connection Error", msg=data.message)
            PostEvent(self.prsnt.frame, evt)
            return
        busy.Destroy()
        try:
            wx.Yield()
        except Exception:
            # this exception is a wx._core.PyAssertionError which for some
            # reason I can't explicitly catch so I'm using a catch all here.
            # this error is raised when wx.Yield is called recursively
            pass
        del(busy)
        self.prsnt.clear_dark_ref.Enable()
        self.prsnt.confirmation_message("Dark Reference Saved", "Success!")
        device.dark_ref_taken = True
        auto_int = self.abstr.auto_integrate
        self.set_auto_integration(False)
        self.prsnt.auto_integration.SetValue(False)
        if cont_play:
            self.start_plot_threads()
        else:
            self.take_and_plot_snapshot()
            self.set_auto_integration(auto_int)
            self.prsnt.auto_integration.SetValue(auto_int)

    def set_light_reference(self):
        """save a light reference spectrum for reflectance/transmittance"""
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        cont_play = False
        if self.active_threads:
            msg = "You'll need to exit Continuous Measurement mode to take a " \
                "\nnew light reference. "
            self.prsnt.confirmation_message("Light Reference", msg)
            return
        device = self.active_device
        if not device:
            return
        msg = "Illuminate the sensor head with reference lamp, then press \n" \
            "'OK' to save the light reference"
        proceed = self.prsnt.ok_cancel("Light Reference", msg)
        if not proceed:
            return
        busy = self.prsnt.busy("Taking Light Reference Scan")
        try:
            data = device.get_pixel_data()
            temp = device.get_internal_temp()
            temperature_compensation = AT * temp ** 3 + \
                BT * temp ** 2 + CT * temp
            device.light_reference = [i - 1500 - temperature_compensation for i in data]
        except DeviceCommunicationError, data:
            busy = None
            del(busy)
            evt = event_error(title="Connection Error", msg=data.message)
            PostEvent(self.prsnt.frame, evt)
            return
        busy = None
        del(busy)
        self.prsnt.confirmation_message("Light Reference Saved",
                                               "Success!")

    def clear_dark_ref(self):
        """sets dark reference to null"""
        device = self.active_device
        if not device:
            return
        if not device.dark_reference:
            self.prsnt.confirmation_message(
                "The active device does not have a saved dark scan.",
                "No Dark Reference")
            return
        else:
            device.dark_reference = []
            device.dark_ref_taken = False
        self.prsnt.confirmation_message(
            "Dark Reference has been removed", "Success!")

    def copy_plot_to_clipboard(self):
        """copys the plot area to the system clipboard as an image"""
        self.prsnt.copy_plot_to_clipboard(gettempdir())
        msg = "Your image has been copied to the system clipboard"
        self.prsnt.confirmation_message(msg, "Success!")

    def compute_derivative(self, data):
        """performs a very rudimentary numerical derivative of the data set.
        because our steps in the x axis are one, no division is necessary"""
        i = 1
        derivative = []
        while i < self.abstr.x_data_range[1] - self.abstr.x_data_range[0] + 1:
            derivative.append((data[i] - data[i-1]))
            i += 1
        derivative.append(0.0)
        return derivative

    def compute_and_plot_first_derivative(self):
        """computes derivative and plots the outcome"""
        if not self.abstr.y_data:
            msg = "Please take a reading before attempting this function.\n"
            self.prsnt.give_error("No Scan Data", msg)
            return
        first_derivative = self.compute_derivative(self.abstr.y_data[0])
        self.prsnt.plot_signal(first_derivative, "First Derivative")

    def compute_and_plot_second_derivative(self):
        """computes the derivative twice and plots the outcome"""
        if not self.abstr.y_data:
            msg = "Please take a reading before attempting this function.\n"
            self.prsnt.give_error("No Scan Data", msg)
            return
        first_derivative = self.compute_derivative(self.abstr.y_data[0])
        second_derivative = self.compute_derivative(first_derivative)
        self.prsnt.plot_signal(second_derivative, "Second Derivative")

    def update_integration_time(self):
        """lets the thread know a new user specified integration time needs to
        be set"""
        self.abstr.integ_time = self.prsnt.integ_time
        for device in self.devices:
            device.update_integ.set()

    def set_auto_integration(self, auto_on):
        """resets the device to auto-integration and lets the thread know a new
        integration time needs to be set"""
        self.abstr.auto_integrate = auto_on
        for device in self.devices:
            device.update_integ.set()
        self.prsnt.integration_time.Enable(not auto_on)
        if not auto_on:
            if self.abstr.connected:
                self.prsnt.integration_time.SetValue(
                    self.active_device.prev_integ/1000)
                self.abstr.integ_time = self.active_device.prev_integ

    def set_auto_scale(self, auto_on):
        self.prsnt.set_auto_scale(not auto_on)

    def update_number_of_scans_to_average(self):
        """lets the thread know a new number of average scans needs to be set"""
        self.abstr.average_scans = self.prsnt.average_scans
        for device in self.devices:
            device.update_average_scans.set()

    def update_mode_and_units(self):
        """since plot signal checks the graph mode before each plot, this method
        enables units and tells thread to update units"""
        self.prsnt.enable_units()
        self.active_mode = self.prsnt.active_mode
        self.active_unit = self.prsnt.active_unit
        d = False
        for device in self.devices:
            device.change_units.set()

    def validate_and_update_y_axis(self):
        """make sure miniminum value is less than maximum value and update
        prsnt"""
        maxy = self.prsnt.max_y
        miny = self.prsnt.min_y
        if miny == '-' or maxy == '-':
            return
        if miny > maxy:
            self.prsnt.set_background_color(
                self.prsnt.y_axis_max, "Red")
            return
        try:
            float(miny)
            float(maxy)
        except ValueError:
            self.prsnt.set_background_color(
                self.prsnt.y_axis_max, "Red")
            return
        if miny == maxy:
            maxy += 0.01
        self.prsnt.y_axis_limits = (miny, maxy)
        self.prsnt.set_background_color(
            self.prsnt.y_axis_max, "White")
        self.prsnt.draw()

    def validate_and_update_x_axis(self):
        """make sure miniminum value is less than maximum value and update
        prsnt"""
        maxx = self.prsnt.max_x
        minx = self.prsnt.min_x
        if minx == '-' or maxx == '-':
            return
        if minx > maxx:
            self.prsnt.set_background_color(
                self.prsnt.x_axis_max, "Red")
            return
        try:
            float(minx)
            float(maxx)
        except ValueError:
            self.prsnt.set_background_color(
                self.prsnt.y_axis_max, "Red")
            return
        self.prsnt.x_axis_limits = (minx, maxx)
        self.prsnt.set_background_color(
            self.prsnt.x_axis_max, "White")
        self.prsnt.draw()

    def reset_original_plot(self):
        """refresh the current plot with orginal zoom/axes settings"""
        if self.abstr.multi_plot_data:
            self.prsnt.refresh_plot_defaults(
                multi_plot=self.abstr.multi_plot_data)
        else:
            if self.active_mode == PHOTON_FLUX:
                self.abstr.y_data[0] = self.calculate_ypf(
                    range(self.abstr.x_data_range[0], self.abstr.x_data_range[1] + 1),
                    self.abstr.y_data[0][:self.abstr.x_data_range[1] + 1 - self.abstr.x_data_range[0]])
            elif self.active_mode in [ENERGY_FLUX]:
                self.abstr.y_data[0] = self.integrate_range(
                    range(self.abstr.x_data_range[0], self.abstr.x_data_range[1] + 1),
                    self.abstr.y_data[0][:self.abstr.x_data_range[1] + 1 - self.abstr.x_data_range[0]])
            self.prsnt.refresh_plot_defaults(
                self.abstr.x_data_range, self.abstr.y_data)

    def toggle_average(self):
        """when plotting multiple lines, this method turns on and off the
        average plot"""
        self.prsnt.toggle_average()

    def change_plot_view(self, mode, units):
        """this method handles the menu -> view selection and lets the thread
        know it needs to update"""
        self.stop_all_threads()
        self.prsnt.active_mode = mode
        if units is not None:
            self.prsnt.active_unit = units
        self.prsnt.enable_units()
        d = False
        for device in self.devices:
            device.change_units.set()
        try:
            if self.active_threads:
                return
        except Exception:
            pass
        self.take_and_plot_snapshot()

    def set_calibrate_mode(self):
        """adds a few extra buttons and allows pixel picker event"""
        self.stop_all_threads()
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        self.prsnt.set_calibration_mode(len(self.devices),
                                        self.light_reference_cal,
                                        self.set_hot_pixel,
                                        self.device_reference_cal)

    def set_hot_pixel(self, event):
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        device = self.active_device
        if not device:
            return
        wavelength = self.prsnt.get_hot_wavelength(device)
        if wavelength is not None:
            success = device.add_hot_pixel_at_wavelength(wavelength)
            if not success:
                add_one = self.prsnt.ok_cancel("Hot Pixel Error",
                                      "This pixel has already been added to " \
                                      " the dead pixel array.\nAdd one to " \
                                      "the pixel index?")
                if add_one:
                    success = device.add_hot_pixel_at_wavelength(wavelength, add_one)
                    if not success:
                        self.prsnt.give_error("Hot Pixel Error",
                                              "This ones been added already too.")
        else:
            self.prsnt.give_error("Hot Pixel Error",
                                  "Make sure your bad wavelength is selected first.")

    def light_reference_cal(self, event):
        """gives user instruction on how to take calibration scan, takes the
        scan, and writes it to calibration memory"""
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        msg = "Place the sensor under the calibration light and press OK to\n" \
            " take a Calibration Scan"
        cont = self.prsnt.ok_cancel("Calibration Scan", msg)
        if not cont:
            return
        device = self.active_device
        if not device:
            return
        self.calibrate(device, LOCK_IN_CALIBRATION)

    def calibrate(self, device, lock_code):
        self.prsnt.active_mode = RELATIVE
        self.prsnt.enable_units()
        device.irrad_unit = COUNTS
        try:
            device.get_spectrum()
            device.calibration_scan = device.y_data
        except DeviceCommunicationError, data:
            self.prsnt.give_error("Connection Error", data.message)
            return
        self.prsnt.plot_signal(device.calibration_scan,
                               "Calibration Scan")
        self.prsnt.integ_time = self.abstr.integ_time = device.prev_integ
        msg = "Do you want to keep the current calibration scan?\n"
        cont = self.prsnt.ok_cancel("Keep Scan?", msg)
        if not cont:
            return
        if lock_code == LOCK_IN_CALIBRATION:
            calibration_file = self.prsnt.calibration_file_dialog(
                self.abstr.current_directory)
            if not calibration_file:
                return
            calibration_data = self.parse_and_compute_calibration_data(
                calibration_file, device)
        else:
            calibration_data = device.calibration_scan
        calibration_data[-1] = device.prev_integ
        msg = "Press okay to overwrite calibration data."
        cont = self.prsnt.ok_cancel("Are you sure?!", msg)
        if not cont:
            return
        try:
            device.set_irradiance_calibration(calibration_data)
        except DeviceCommunicationError, data:
            self.prsnt.give_error("Connection Error", data.message)
            return
        self.prsnt.confirmation_message(
            "Calibration data has been saved", "Success!")

    def device_reference_cal(self, event):
        if not len(self.devices) >= 2:
            msg = "You need a minimum of 2 reference devices to use this " \
                "function."
            self.prsnt.give_error("Calibration Error", msg)
            return
        msg = "Place the sensors under the calibration light and press OK to\n" \
            " take a Calibration Scan"
        cont = self.prsnt.ok_cancel("Calibration Scan", msg)
        if not cont:
            return
        self.prsnt.active_mode = RELATIVE
        self.prsnt.enable_units()
        device = self.active_device
        for dev in self.devices:
            if dev == device:
                dev.irrad_unit = COUNTS
            else:
                dev.irrad_unit = MICRO_MOLES
            dev.change_units.clear()
            # we want at least a 5 scan average of all devices
            self.prsnt.average_scans = 5
            self.abstr.average_scans = 5
            dev.update_average_scans.set()
        for dev in self.devices:
            try:
                self.spectrum_snapshot(dev)
            except DeviceCommunicationError, data:
                self.prsnt.give_error("Connection Error", data)
                return
        self.device_ref_cal_snapshot()
        if len(self.abstr.multi_plot_data) != len(self.devices):
            # something went wrong somewhere
            return
        self.prsnt.integ_time = self.abstr.integ_time = device.prev_integ
        msg = "Do you want to keep the current calibration scan and write\n" \
            "calibration data to device: %s?" % device.name
        cont = self.prsnt.ok_cancel("Keep Scan?", msg)
        if not cont:
            return
        # get the average output of all calibration devices
        avg_scan_data = [0] * len(device.x_data)
        for dev in self.devices:
            if dev is not device:
                i = 0
                for y in dev.calibration_scan:
                    avg_scan_data[i] += y
                    i += 1
        avg_scan_data = map(lambda x: x/(len(self.devices)-1), avg_scan_data)
        i = 0
        calibration_data = []
        for y in avg_scan_data:
            calibration_data.append(y/device.calibration_scan[i])
            i += 1
        try:
            device.set_calibration_data(calibration_data)
        except DeviceCommunicationError, data:
            self.prsnt.give_error("Connection Error", data)
        self.prsnt.confirmation_message(
            "Calibration data has been saved", "Success!")

    def device_ref_cal_snapshot(self):
        self.prsnt.show_average_button.SetValue(False)
        plot_data = []
        for dev in self.devices:
            dev.prev_integ = int(
                dev.get_reversed_float(DA_ADDR_INTEGRATION))
            scan_data = {}
            scan_data['x_data'] = dev.x_data
            scan_data['labels'] = [dev.name]
            y = dev.get_spectrum()
            # we will return here instead of continue because we do not want
            # this methods to succeed if one of the calibration device scans
            # have failed
            if not y:
                return
            dev.calibration_scan = y
            scan_data['y_data'] = [y]
            plot_data.append(scan_data)
        self.abstr.multi_plot_data = plot_data
        self.prsnt.plot_multiline(self.abstr.multi_plot_data,
                                         average=False)

    def parse_and_compute_calibration_data(self, file_path, device):
        with open(file_path, 'r') as cal_file:
            file_content = cal_file.readlines()[7:]
        lamp_output = [0] * 821
        for line in file_content:
            line = line.split()
            lamp_output[int(line[0]) - 280] = float(line[1])
        for i in range(0, len(lamp_output) - 1, 5):
            j = 1
            while j < 5:
                lamp_output[i + j] = ((lamp_output[i + 5] - \
                                       lamp_output[i])/5 * j) + lamp_output[i]
                j += 1
        # index 0 of lamp_output is for wavelength 280. our starting index needs
        # to be the starting data range - 280
        lamp_output += [0]
        calibration_factors = []
        i = device.x_data[0] - 280
        for counts in device.calibration_scan:
            calibration_factors.append(lamp_output[i]/counts)
            i += 1
        return calibration_factors

    def take_and_plot_snapshot(self):
        """takes a single measurement and plots it to the screen"""
        self.stop_all_threads()
        if not self.abstr.connected:
            self.connect_to_device()
            if not self.abstr.connected:
                return
        self.prsnt.show_average_button.SetValue(False)
        self.abstr.multi_plot_data = []
        self.abstr.y_data = []
        if self.prsnt.active_mode == RT:
            for device in self.devices:
                if not (device.light_reference and device.dark_reference):
                    msg = "Please take a Dark and Light Reference point for %s" \
                        "\n before attempting to plot Reflectance/Transmittance"
                    self.prsnt.give_error("No Light/Dark Reverence",
                                                 msg % device.name)
                    return
        self.prsnt.current_process("Plotting Snapshot")
        busy = self.prsnt.busy("Taking a measurement...")
        try:
            wx.Yield()
        except Exception:
            # this exception is a wx._core.PyAssertionError which for some
            # reason I can't explicitly catch so I'm using a catch all here.
            # this error is raised when wx.Yield is called recursively
            pass
        for dev in self.devices:
            if dev.change_units.is_set():
                if self.prsnt.active_mode in [ENERGY_FLUX, ILLUMINANCE]:
                    dev.irrad_unit = WATTS_PER_METER_SQUARED
                    if self.prsnt.active_unit == LUX:
                        self.prsnt.label = LUX_LABEL
                    elif self.prsnt.active_unit == FOOTCANDLE:
                        self.prsnt.label = FC_LABEL
                    else:
                        self.prsnt.label = WM2_LABEL
                elif self.prsnt.active_mode == PHOTON_FLUX:
                    dev.irrad_unit = MICRO_MOLES
                    self.prsnt.label = MICROMOL_LABEL
                elif self.prsnt.active_mode == RT:
                    dev.irrad_unit = COUNTS
                    self.prsnt.label = r'Reflectance/Transmittance [$\%$]'
                else:
                    dev.irrad_unit = COUNTS
                    self.prsnt.label = r'Counts'
                dev.change_units.clear()
            if dev.update_integ.is_set():
                dev.auto_integration = self.abstr.auto_integrate
                if not dev.auto_integration:
                    dev.set_integration_period(self.abstr.integ_time)
                dev.update_integ.clear()
            if dev.update_average_scans.is_set():
                dev.set_scans_to_avg(self.abstr.average_scans)
                dev.update_average_scans.clear()
        if len(self.devices) > 1:
            for dev in self.devices:
                dev.start_measurement()
            inc = ((self.devices[-1].prev_integ/1000000.0 + 0.01) * \
                   self.devices[-1].avg_scans)/10
            for i in range(10):
                sleep(inc)
                wx.YieldIfNeeded()
            self.pull_multi_device_data()
            self.prsnt.integ_time = self.abstr.integ_time = \
                self.active_device.prev_integ
            self.prsnt.current_process("")
            busy = None
            del(busy)
            return
        device = self.active_device
        if not device:
            self.prsnt.current_process("")
            return
        try:
            self.get_active_signal_data(device)
        except DeviceCommunicationError, data:
            self.prsnt.current_process("")
            self.prsnt.give_error("Connection Error", data.message)
            return
        self.abstr.y_data = [device.y_data]
        self.prsnt.plot_signal(device.y_data, device.name)
        self.prsnt.integ_time = self.abstr.integ_time = device.prev_integ
        self.prsnt.current_process("")
        device.data_ready.clear()
        busy = None
        del(busy)

    def pull_multi_device_data(self):
        plot_data = []
        for device in self.devices:
            try:
                scan_data = {}
                scan_data['x_data'] = device.x_data
                scan_data['labels'] = [device.name]
                device.acquire_measurement(self.prsnt.active_mode == RT)
                if self.prsnt.active_unit == LUX:
                    device.y_data = self.calculate_lux(device.y_data, device.x_data)
                elif self.prsnt.active_unit == FOOTCANDLE:
                    device.y_data = self.calculate_lux(device.y_data, device.x_data,
                                                       fc=True)
                if self.prsnt.active_mode in [ENERGY_FLUX, ILLUMINANCE]:
                    device.y_data = self.integrate_range(device.x_data, device.y_data)
                if self.prsnt.active_mode == ILLUMINANCE:
                    del device.y_data[-2:]
                elif self.prsnt.active_mode == PHOTON_FLUX:
                    device.y_data = self.calculate_ypf(device.x_data, device.y_data)
                # we will continue here instead of return in the case of one
                # device failing but the other's do not. software will still
                # plot the data from the devices who do not fail
                scan_data['y_data'] = [device.y_data]
                plot_data.append(scan_data)
            except DeviceCommunicationError, data:
                self.prsnt.give_error("Connection Error", data.message)
        plot_data = sorted(plot_data,
                           key=lambda scan: scan['labels'][0])
        paired = []
        for dev in self.devices:
            if dev.paired:
                already_paired = False
                for p in paired:
                    if dev.name in p:
                        already_paired = True
                if not already_paired:
                    paired.append((dev.name, dev.paired))
        self.abstr.multi_plot_data = plot_data
        self.prsnt.plot_multiline(self.abstr.multi_plot_data, average=False,
                                  active_device=self.active_device.name,
                                  paired=paired)

    def update_vlines(self):
        self.prsnt.update_vlines()
        self.reset_original_plot()

    # close apogee spectrovision
    def shutdown_application(self):
        self.prsnt.frame.Close()

    def stop_all_threads(self, shutdown=False):
        self.prsnt.color_map.Enable()
        self.prsnt.current_process("")
        self.start_thread.clear()
        self.stop_thread.set()
        self.active_threads = []
        if shutdown:
            from threading import active_count
            while active_count() < 1:
                sleep(0.1)

    def pause_all_threads(self):
        self.prsnt.color_map.Enable()
        self.prsnt.current_process("Paused...")
        self.pause_thread.set()

    def right_click_menu(self, event):
        self.old_name = event.GetEventObject().GetLabel()
        v = n = paired = False
        for dev in self.devices:
            if dev.name == self.old_name:
                if dev.x_data[0] == 340 and dev.paired == False:
                    v = True
                elif dev.x_data[0] == 635 and dev.paired == False:
                    n = True
                if dev.paired:
                    paired = True
                break
        if v:
            for dev in self.devices:
                if dev.x_data[0] == 635 and dev.paired == False:
                    n = True
                    break
        elif n:
            for dev in self.devices:
                if dev.x_data[0] == 340 and dev.paired == False:
                    v = True
                    break
        self.prsnt.pop_up_menu(self.process_choice, v and n, paired)

    def process_choice(self, event):
        choice = event.GetId()
        if choice == 0:
            # rename sensor
            name = self.prsnt.rename_device(self.old_name)
            if not name:
                name = self.old_name
            for device in self.devices:
                if device.name == self.old_name:
                    device.name = name
                    device.set_device_alias(name)
                    break
            for sensor in self.prsnt.sensors:
                if sensor.GetLabel() == self.old_name:
                    sensor.SetLabel(name)
                    sensor.Fit()
                    sensor.Refresh()
                    break
            self.prsnt.tool_bar.Realize()
        elif choice == 1:
            # disconnect sensor
            dev = [i for i in self.devices if i.name == self.old_name][0]
            self.disconnect(dev)
            self.prsnt.confirmation_message("Device has been disconnected.",
                                            "Success!")
        elif choice == 2:
            # pair sensors
            for dev in self.devices:
                if self.old_name == dev.name:
                    selected = dev
                    break
            if selected.x_data[0] == 340:
                find_nir = True
            else:
                find_nir = False
            choices = []
            for dev in self.devices:
                if find_nir == True and dev.x_data[0] == 635 and dev.paired is False:
                    choices.append(dev.name)
                elif find_nir == False and dev.x_data[0] == 340 and dev.paired is False:
                    choices.append(dev.name)
            if len(choices) == 1:
                pair_with = choices[0]
            else:
                pair_with = self.prsnt.get_sensor_pair(selected.name, choices)
            if pair_with:
                for dev in self.devices:
                    if pair_with == dev.name:
                        dev.paired = selected.name
                        selected.paired = dev.name
                        self.prsnt.set_pair((selected.name, dev.name))
                        break
        elif choice == 3:
            # unpair sensors
            for dev in self.devices:
                if self.old_name == dev.name:
                    paired = dev.paired
                    dev.paired = False
                    break
            for dev in self.devices:
                if paired == dev.name:
                    dev.paired = False
                    break
            self.prsnt.remove_pair((self.old_name, paired))
        elif choice == 4:
            # reset spec
            busy = wx.BusyInfo("Resetting sensor %s" % self.old_name, self.prsnt.frame)
            dev = [i for i in self.devices if i.name == self.old_name][0]
            dev.reset_spec()
            self.disconnect(dev)
            del(busy)
            try:
                wx.Yield()
            except Exception:
                # this exception is a wx._core.PyAssertionError which for some
                # reason I can't explicitly catch so I'm using a catch all here.
                # this error is raised when wx.Yield is called recursively
                pass
            self.prsnt.confirmation_message("Device has been reset.",
                                            "Success!")
            self.connect_to_device()
        elif choice == 5:
            # set device serial
            dev = [dev for dev in self.devices if dev.name == self.old_name][0]
            old_serial = dev.get_device_serial()
            serial = self.prsnt.reserialize_device(old_serial)
            if not serial:
                return
            else:
                dev.set_device_serial(serial)
        elif choice == 6:
            dev = [dev for dev in self.devices if dev.name == self.old_name][0]
            dev.reset_default_settings()
        elif choice == 7:
            dev = [dev for dev in self.devices if dev.name == self.old_name][0]
            dev.change_rs232_baudrate(115200)
        self.old_name = None
        del(self.old_name)

    def update_red_farred(self):
        new_ranges = self.prsnt.get_red_farred(self.abstr.red_farred)
        if new_ranges is not None:
            self.abstr.red_farred = str(new_ranges)
            self.prsnt.update_red_farred(new_ranges)

    def check_for_updates(self):
        return # don't know if mesa user's would want this or not
        request = urllib2.Request("http://www.apogeeinstruments.com/downloads/")
        response = None
        try:
            response = urllib2.urlopen(request)
        except (Exception, urllib2.URLError), data:
            print data
            # maybe we're international?
            try:
                request = urllib2.Request("http://www.apogeeinstruments.co.uk/downloads")
                response = urllib2.urlopen(request)
            except (Exception, urllib2.URLError), data:
                print data
                return
        if response is not None:
            try:
                page_data = response.read()
                version = page_data.split('ApogeeSpectrovision PC v ')[1][:8]
                if version > VERSION:
                    self.prsnt.present_update_message(request.get_full_url())
            except Exception, data:
                print data

    def update_spin_ctrls(self, widget):
        self.prsnt.number_pad(widget)
        if widget == self.prsnt.integration_time:
            self.update_integration_time()
        elif widget == self.prsnt.number_of_scans_to_avg:
            self.update_number_of_scans_to_average()
        elif type(widget) == wx.SpinCtrl:
            self.update_vlines()
        else:
            self.validate_and_update_x_axis()
            self.validate_and_update_y_axis()

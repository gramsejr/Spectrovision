# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import csv
import datetime
import itertools
import gc
import os
import sys
import time
from Queue import Queue, Empty
from tempfile import gettempdir
from threading import Event, Thread
from time import sleep

from serial.tools.list_ports import comports
import usb.util
import usb.core
import wx
import wx.lib.newevent
from wx import PostEvent, Yield

from constants import *
from USB_Instrument import Instrument, DeviceCommunicationError

event_error, EVT_ERROR = wx.lib.newevent.NewEvent()
plot_event, PLOT_EVT = wx.lib.newevent.NewEvent()
status_event, STATUS_EVT = wx.lib.newevent.NewEvent()
toolbar_event, TOOLBAR_EVT = wx.lib.newevent.NewEvent()


class ASControl(object):
    def __init__(self, abstraction, interaction, presentation):
        self.abstraction = abstraction
        self.presentation = presentation
        self.data_capture_queue = Queue()
        self.plot_data_queue = Queue()
        self.start_thread = Event()
        self.start_thread.clear()
        self.stop_thread = Event()
        self.pause_thread = Event()
        self.hold_thread = Event()
        self.devices = []
        self.active_threads = []
        interaction.install(self, presentation)

    @property
    def active_device(self):
        dev_name = self.presentation.active_device
        if not dev_name:
            msg = "Please connect a device before attempting this function."
            evt = event_error(title="No Device Selected", msg=msg)
            PostEvent(self.presentation.frame, evt)
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
            file_paths = self.presentation.open_data_file_dialog(
                self.abstraction.current_directory)
            if not file_paths:
                return
        # update directory and file for persistence purposes
        self.abstraction.current_directory = os.path.dirname(file_paths[0])
        self.abstraction.current_file = os.path.basename(file_paths[0])
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
            data = zip(*rows)
            x_data = list(data[0][2:-6])
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
                # if elements[0] == timestamp, then we have encountered a file
                # with data from two different sensors. start a new dictionary
                # as if the following data was from a seperate file
                if elements[0] == 'Timestamp':
                    file_contents.append(dictionary)
                    dictionary = {}
                    dictionary['labels'] = []
                    while True:
                        try:
                            elements.remove('-')
                        except ValueError:
                            break
                    dictionary['x_data'] = map(lambda x: float(x), elements[2:-6])
                    dictionary['y_data'] = []
                    j += 1
                    elements = data[j]
                dictionary['labels'].append(elements[0])
                y_data = list(elements[2:-2]) # exclude temperature
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
        self.abstraction.y_data = []
        self.abstraction.multi_plot_data = file_contents
        self.presentation.show_average_button.Enable()
        self.presentation.plot_multiline(file_contents)

    def save_spectrum(self):
        """
        saves the current spectrum as an image file of the users choice
        """
        file_path = self.presentation.save_spectrum_dialog(
            self.abstraction.current_directory,
            os.path.splitext(self.abstraction.current_file)[0])
        if not file_path:
            return
        self.abstraction.current_file = os.path.basename(file_path)
        self.abstraction.current_directory = os.path.dirname(file_path)
        self.presentation.save_graph(file_path)

    def setup_data_capture(self):
        """
        intializes/prompts user for data capture settings and begins data
        capture threads. If user entered a start time, this method will wait
        until specified time before starting threads. DISCLAIMER: timing may
        not be exact.
        """
        self.stop_all_threads()
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        settings = self.presentation.data_capture_settings_dlg()
        if not settings:
            return
        cont = True
        # get a filepath for each device connected
        for device in self.devices:
            if self.presentation.active_mode == RT:
                if not (device.dark_ref_list[0] and device.light_reference):
                    msg = "Please take a Dark and Light Reference point for %s" \
                    "\n before attempting to plot Reflectance/Transmittance"
                    self.presentation.give_error("No Light/Dark Reference",
                                                 msg % device.name)
                    cont = False
                    continue
            suggested_name = device.name
            file_path = ''
            if settings['save_to_file']:
                file_path = self.presentation.save_data_dialog(
                    self.abstraction.current_directory, suggested_name)
                if not file_path:
                    msg = "Could not retrieve a file name. Do you want to " \
                        "proceed without saving data for device %s?" 
                    title = "No Filepath Given"
                    proceed = self.presentation.ok_cancel(title,
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
                if self.abstraction.auto_integrate:
                    device.auto_integration = True
                else:
                    device.auto_integration = False
                    device.set_integration_period(self.presentation.integ_time)
                device.set_scans_to_avg(int(self.presentation.average_scans))
            except DeviceCommunicationError, data:
                self.presentation.give_error("Connection Error %s" % device.name,
                                             data.message)
        if not cont:
            return
        self.abstraction.multi_plot_data = []
        if settings['start_time']:
            start_time = (settings['start_time'] - datetime.datetime.utcfromtimestamp(0)).total_seconds()
            dlg = self.presentation.gen_prog_dlg("Data Capture Countdown",
                                                 "Your data capture application will start at: \n %s" % settings['start_time'].strftime("%H:%M:%S"),
                                                 0)
            t = -1
            while t < 0:
                t = (time.time() - time.timezone) - start_time
                cont, skip = dlg.Pulse()
                if not cont:
                    return
                sleep(0.01)
            dlg.Close()
            dlg.Destroy()
        self.data_capture_thread = Thread(target=self.collect_raw_data,
                                          args=(settings['total_scans'],
                                                settings['time_between_scans'],
                                                settings['plot_to_screen'],
                                                settings['log_temperature'],
                                                self.presentation.active_mode,
                                                self.presentation.active_unit,
                                                self.presentation.integ_lines))
        self.data_capture_thread.daemon = True
        self.data_capture_thread.start()
        proceed = self.presentation.progress_dialog(
            settings['total_scans'], self.data_capture_generator)
        if not proceed:
            self.stop_thread.set()

    def data_capture_generator(self, total_scans):
        """
        because wxpython has issues with threads other than the main thread
        updating the gui, this generator reads data from a thread safe queue in
        the main thread and yields the values to update the progress dialog.
        The queue is updated by a worker thread running self.collect_raw_data.
        """
        current_scan = 1
        while not self.data_capture_queue.empty():
            self.data_capture_queue.get()
        while True:
            try:
                current_scan = self.data_capture_queue.get_nowait()
            except Empty:
                wx.YieldIfNeeded()
                pass
            else:
                if current_scan == -1:
                    return
            yield current_scan

    def collect_raw_data(self, total_scans, time_between_scans, plot, log_temp,
                         active_mode=0, active_unit=0, integ_range=None):
        """
        collects data during data capture process and writes it to a file after
        each scan. if no file is chosen, data is written to a temp file. have
        to pass in the plot mode and units mode because presentation is too busy
        with the progress dialog to respond
        """
        self.stop_thread.clear()
        scan_data = []
        self.abstraction.y_data = []
        #float("inf") wasn't working well for XP users
        # 8000000 gives roughly 40 GB of data. Should be sufficient yah?
        if total_scans == 0:
            total_scans = 8000000
        i = 0
        if not time_between_scans:
            time_between_scans = 0
        # if total scans is infinite, data collection will proceed until user
        # hits cancel on the generator controlled progress dialog. the dialog
        # sets the self.stop_thread Event which is checked here before every
        # scan
        if len(self.devices) > 1:
            multiplot = True
            plot_data = []
        while i < total_scans:
            scan_time = time.time()
            self.data_capture_queue.put(i + 1)
            if self.stop_thread.is_set():
                self.data_capture_queue.put(-1)
                return
            # now collect the data from the devices and save them to their 
            # respective files
            for device in self.devices:
                try:
                    y = device.get_spectrum()
                except DeviceCommunicationError, data:
                    evt = event_error(title="Connection Error %s" % device.name,
                                      msg=data.message)
                    PostEvent(self.presentation.frame, evt)
                if active_mode in [ENERGY_FLUX, ILLUMINANCE]:
                    y = self.integrate_range(device.x_data, y, integ_range)
                elif active_mode == PHOTON_FLUX:
                    y = self.calculate_ypf(device.x_data, y, integ_range)
                elif active_unit == LUX:
                    y = self.calculate_lux(y, device)
                elif active_unit == FOOTCANDLE:
                    y = self.calculate_lux(y, device, fc=True)
                self.abstraction.y_data = [y]
                temp = None
                if log_temp:
                    temp = device.prev_temp
                self.save_data_to_file(device.file_path,
                                       'r+',
                                       [device.x_data[0],
                                        device.x_data[-1]],
                                       temp,
                                       active_mode,
                                       active_unit)
                #if multiplot:
                    #scan = {}
                    #scan['y_data'] = [y]
                    #scan['labels'] = [device.name]
                    #scan['x_data'] = device.x_data
                    #plot_data.append(scan)
            #if multiplot:
                #plot_data = sorted(plot_data, key=lambda scan: scan['labels'][0])
                #evt = plot_event(multiline=True, plot_data=plot_data,
                                 #average=False,
                                 #active_device=self.active_device.name)
                #plot_data = []
            #else:
                #evt = plot_event(plot_data=self.abstraction.y_data, label=self.devices[0].name)
            #PostEvent(self.presentation.frame, evt)

            # if there is a time_between_scans, make sure we hit that point
            # before continuing. otherwise, time_between_scans is roughly
            # the amount of time it takes to pull the data off the registers
            # and save it to the file
            while time.time() - time_between_scans < scan_time:
                if self.stop_thread.is_set():
                    self.data_capture_queue.put(-1)
                    return
                if (i + 1) == total_scans:
                    break
                sleep(0.01)
            i += 1
        # the next line ends the progress dialog
        self.data_capture_queue.put(-1)
        if plot:
            plot_files = []
            for device in self.devices:
                plot_files.append(device.file_path)
            self.plot_from_file(plot_files)

    def save_data_to_file(self, file_path='', mode='r+', x_data=[], sensor_temp=None,
                          active_mode=-1, active_unit=-1):
        """
        takes the data of the current graph and saves it to a file. If the
        file exists and append=True, data is appended to end of file
        if the file is already open it cannot be written too. in this case
        the data is simply thrown away
        """
        if not (self.abstraction.y_data or self.abstraction.multi_plot_data):
            msg = "Please take a reading before attempting this function."
            self.presentation.give_error("No Scan Data", msg)
            return
        if not file_path:
            file_path = self.presentation.save_data_dialog(
                self.abstraction.current_directory,
                os.path.splitext(self.abstraction.current_file)[0])
            if not file_path:
                return
        path_exists = os.path.exists(file_path)
        self.abstraction.current_directory = os.path.dirname(file_path)
        self.abstraction.current_file = os.path.basename(file_path)
        content = []
        if active_mode < 0:
            active_mode = self.presentation.active_mode
        if active_unit < 0:
            active_unit = self.presentation.active_unit
        # create single plot data
        if not self.abstraction.multi_plot_data:
            self.abstraction.current_file_type = self.devices[0].sensor_type
            non_matching = self.abstraction.current_file_type != self.abstraction.last_file_type
            column1 = []
            if not path_exists or non_matching:
                column1 = ['Timestamp', 'Units'] + self.devices[0].x_data
                column1 += ['-'] * (483-len(column1))
                column1 += ['Integration Time (ms)','Integrated Total', 'PPF',
                            'YPF', 'PPE', 'Sensor Temp']
                if not non_matching:
                    mode = 'w'
            content = ['%s %s' % (
                datetime.datetime.now().strftime("%H:%M:%S %Y-%m-%d"),
                self.devices[0].name), MODE_TO_UNITS[active_mode]]
            if self.abstraction.current_file_type == 'NIR':
                content += self.abstraction.y_data[0][:466] + ['-'] * 15 + \
                    self.abstraction.y_data[0][466:]
            else:
                content += self.abstraction.y_data[0]
            if active_mode == 4: #lux or fc
                content[1] = content[1] % UNITS_TO_STR[active_unit]
            if column1:
                content = list(itertools.izip_longest(column1, content,
                                                      fillvalue='-'))
            else:
                content = zip(content)
        # create multiplot data
        else:
            content = []
            for scan_data in self.abstraction.multi_plot_data:
                header = ['Timestamp', 'Units'] + list(scan_data['x_data'])
                header += ['-'] * (483 - len(header))
                header += ['Integration Time (ms)', 'Integrated Total', 'PPF',
                           'YPF', 'PPE', 'Sensor Temp']
                header = zip(header)
                i = 0
                for y_data in scan_data['y_data']:
                    new_col = ['%s %s' % (
                        datetime.datetime.now().strftime("%H:%M:%S %Y-%m-%d"),
                        scan_data['labels'][i]), MODE_TO_UNITS[active_mode]]
                    if len(y_data) < 480:
                        new_col += y_data[:466] + ['-'] * 15 + y_data[466:]
                    else:
                        new_col += y_data
                    if active_mode == 4:
                        new_col[2] = new_col[2] % UNITS_TO_STR[active_unit]
                    i += 1
                    new_col = zip(new_col)
                    temp = []
                    for a, b in itertools.izip_longest(header, new_col,
                                                       fillvalue='-'):
                        temp.append(tuple(a) + tuple(b))
                    header = temp
                if content:
                    temp = []
                    for a, b in itertools.izip_longest(content, header,
                                                       fillvalue='-'):
                        temp.append(tuple(a) + tuple(b))
                    content = temp
                else:
                    content = header
        try:
            if mode == 'r+' and path_exists:
                # this means we are appending a new column onto preexisting data
                # this could get very costly for huge files. We are going to
                # assume that people aren't going to log for weeks at a time
                # when connected to the software.
                prev_content = []
                with open(file_path, 'r') as data_file:
                    reader = csv.reader(data_file)
                    for row in reader:
                        prev_content.append(tuple(row))
                    temp = []
                    if prev_content:
                        for a, b in itertools.izip_longest(prev_content,
                                                           content,
                                                           fillvalue='-'):
                            temp.append(tuple(a) + tuple(b))
                        content = temp
            if sensor_temp:
                temp_entries = list(content[-1])
                temp_entries[-1] = sensor_temp
                content[-1] = tuple(temp_entries)
            with open(file_path, 'w') as data_file:
                writer = csv.writer(data_file, lineterminator='\n')
                writer.writerows(content)
        except IOError, data:
            evt = event_error(title="File IO Error",
                              msg="Could not open file %s\n\n Make sure its " \
                              "not open somewhere and try again." % file_path)
            PostEvent(self.presentation.frame, evt)
        else:
            self.abstraction.last_file_type = self.abstraction.current_file_type
        del(temp_entries)
        del(temp)
        del(prev_content)
        del(reader)
        del(writer)
        del(content)
        del(column1)

    def connect_to_device(self):
        """connects to device, updates the spectrum, sets wavelength for the
        device, and updates presentation to reflect new settings"""
        self.stop_all_threads()
        try:
            possible = usb.core.find(find_all=True,
                                     idVendor=0x2457,
                                     idProduct=0x4000)
            possible = [dev for dev in possible]
            if not possible:
                self.presentation.give_error('Device Not Connected',
                                             'There is no spectroraiometer connected to this computer.')
                return
            serial_numbers = [dev.serial_number[2:6] for dev in possible]
            for s in serial_numbers:
                if s in self.abstraction.connected_serials:
                    serial_numbers.remove(s)
            if len(serial_numbers) == 1:
                for x in possible:
                    if x.serial_number[2:6] == serial_numbers[0]:
                        self.devices.append(Instrument(x))
                        serial = serial_numbers[0]
            else:
                serial = self.presentation.connection_settings_query(self.abstraction.device_serial,
                                                                     serial_numbers)
                if serial is None:
                    return
                self.abstraction.device_serial = serial
                for x in possible:
                    if x.serial_number[2:6] == serial:
                        self.devices.append(Instrument(x))
        except DeviceCommunicationError, data:
            print data
            return
        self.abstraction.connected_serials.append(serial)
        device = self.devices[-1]
        self.abstraction.x_data_range = [device.x_data[0], device.x_data[-1]]
        self.presentation.x_axis_limits = (device.x_data[0], device.x_data[-1])
        self.presentation.x_data = device.x_data
        self.abstraction.connected = True
        self.presentation.enable_disconnect()
        self.presentation.add_sensor_to_toolbar(device.name,
                                                self.right_click_menu)
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
        device_to_disconnect = self.presentation.disconnect_dialog(
            current_devices)
        if not device_to_disconnect:
            return
        device_index = current_devices.index(device_to_disconnect)
        device = self.devices[device_index]
        self.presentation.remove_device(device.name)
        device.disconnect_spec()
        self.abstraction.connected_serials.remove(self.devices[device_index].dev.serial_number[2:6])
        self.devices[device_index] = None
        del(self.devices[device_index])
        if not self.devices:
            self.abstraction.connected = False
            self.presentation.enable_disconnect(False)
        while not self.plot_data_queue.empty():
            self.plot_data_queue.get()
        self.presentation.confirmation_message("Device has been disconnected.",
                                               "Success!")
        if len(self.devices) == 1:
            self.presentation.x_data = self.devices[0].x_data

    def start_plot_threads(self):
        """initalizes startup settings, starts a thread to carry out
        plotting and a seperate thread to carry out data retrieval"""
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        self.stop_thread.clear()
        self.pause_thread.clear()
        self.hold_thread.clear()
        evt = status_event(status="Plotting Continuous Reading")
        PostEvent(self.presentation.frame, evt)
        evt = toolbar_event(enable=False)
        PostEvent(self.presentation.frame, evt)
        if self.start_thread.is_set():
            return
        self.start_thread.set()
        for device in self.devices:
            device.change_units.set()
        self.presentation.show_average_button.SetValue(False)
        self.abstraction.multi_plot_data = {}
        plot_thread = Thread(target=self.plot_data, name="Plot Thread")
        plot_thread.daemon = True
        plot_thread.start()
        self.active_threads.append(plot_thread)
        for device in self.devices:
            thread = Thread(target=self.retrieve_data,
                            kwargs={'device': device},
                            name="Data Retrieval Thread %s"
                            % device.name[-1])
            thread.daemon = True
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
            try:
                data = self.plot_data_queue.get(timeout=0.1)
            except Empty:
                pass
            else:
                if multiplot:
                    scan = {}
                    scan['y_data'] = [data[0]]
                    scan['labels'] = [data[1]]
                    scan['x_data'] = data[2]
                    plot_data.append(scan)
                    if len(plot_data) == len(self.devices):
                        # sort the scans according to label/device.name so they
                        # are the same color from plot to plot and in the same
                        # position in the legend. legend position is used to 
                        # determine which data belongs to the active device
                        # in calibrated modes to display integrated totals
                        plot_data = sorted(plot_data,
                                           key=lambda scan: scan['labels'][0])
                        evt = plot_event(multiline=True,
                                         plot_data=plot_data,
                                         average=False,
                                         active_device=self.active_device.name)
                        PostEvent(self.presentation.frame, evt)
                        self.abstraction.multi_plot_data = plot_data
                        plot_data = []
                else:
                    evt = plot_event(plot_data=data[0], label=data[1])
                    PostEvent(self.presentation.frame, evt)
                gc.collect()

    def retrieve_data(self, device):
        """the intent is that the data retrieval thread stays in this loop while
        taking continuous readings"""
        count = 0
        while not self.stop_thread.is_set():
            while (self.pause_thread.is_set()):
                evt = toolbar_event(enable=True)
                PostEvent(self.presentation.frame, evt)
                if self.stop_thread.is_set():
                    evt = toolbar_event(enable=True)
                    PostEvent(self.presentation.frame, evt)
                    evt = status_event(status="")
                    PostEvent(self.presentation.frame, evt)
                    return
                sleep(0.005)
            try:
                y = self.get_active_signal_data(device)
            except DeviceCommunicationError, data:
                evt = event_error(title="Connection Error", msg=data.message)
                PostEvent(self.presentation.frame, evt)
                self.stop_all_threads()
            else:
                if not y:
                    self.stop_all_threads()
                    break
                self.plot_data_queue.put(
                    (y, device.name, device.x_data))
                self.abstraction.y_data = [y]
                evt = status_event(integ_time=device.prev_integ)
                #self.abstraction.integ_time = device.prev_integ
                PostEvent(self.presentation.frame, evt)
                self.hold_thread.set()

            #print count
            #count += 1
            sleep(0.05) # this is to give the gui time to process events
        evt = toolbar_event(enable=True)
        PostEvent(self.presentation.frame, evt)
        evt = status_event(status="")
        PostEvent(self.presentation.frame, evt)

    def wait(self):
        wait_time = max(self.abstraction.integ_time/1000000 * \
                        self.abstraction.average_scans-1, 0)
        sleep(wait_time)

    def get_active_signal_data(self, device):
        """determines which plot mode is active and returns the data
        accordingly"""
        active_mode = self.presentation.active_mode
        if device.update_integ.is_set():
            device.auto_integration = self.abstraction.auto_integrate
            if not device.auto_integration:
                device.set_integration_period(self.abstraction.integ_time)
            device.update_integ.clear()
        if active_mode == RELATIVE:
            y = self.get_relative_signal(device)
        elif active_mode == RT:
            if not (device.dark_reference and device.light_reference):
                msg = "Please take a Dark and Light Reference point for %s" \
                    "\n before attempting to plot Reflectance/Transmittance"
                self.presentation.give_error("No Light/Dark Reference",
                                             msg % device.name)
                return
            y = self.get_reflectance_transmittance(device)
        else:
            y = self.get_irradiance(device)
        return y

    def get_relative_signal(self, device):
        """returns the raw singal as digital counts"""
        if device.change_units.is_set():
            try:
                device.irrad_unit = COUNTS
            except DeviceCommunicationError, data:
                evt = event_error(title="Connection Error", msg=data.message)
                PostEvent(self.presentation.frame, evt)
                return
            device.change_units.clear()
            self.presentation.label = r'$Counts$'
        return device.get_spectrum()

    def get_irradiance(self, device):
        """returns irradiance signal in either micromol or W/m^2"""
        active_mode = self.presentation.active_mode
        active_unit = self.presentation.active_unit
        if device.change_units.is_set():
            try:
                if active_mode == ENERGY_FLUX or active_mode == ILLUMINANCE:
                    device.irrad_unit = WATTS_PER_METER_SQUARED
                    if active_unit == LUX:
                        self.presentation.label = LUX_LABEL
                    elif active_unit == FOOTCANDLE:
                        self.presentation.label = FC_LABEL
                    else:
                        self.presentation.label = WM2_LABEL
                elif active_mode == PHOTON_FLUX:
                    device.irrad_unit = MICRO_MOLES
                    self.presentation.label = MICROMOL_LABEL
            except DeviceCommunicationError, data:
                evt = event_error(title="Connection Error", msg=data.message)
                PostEvent(self.presentation.frame, evt)
                return
            device.change_units.clear()
        y = device.get_spectrum()
        if active_mode in [ENERGY_FLUX, ILLUMINANCE]:
            y = self.integrate_range(device.x_data, y)
        elif active_mode == PHOTON_FLUX:
            y = self.calculate_ypf(device.x_data, y)
        elif active_unit == LUX:
            y = self.calculate_lux(y, device)
        elif active_unit == FOOTCANDLE:
            y = self.calculate_lux(y, device, fc=True)
        return y

    def integrate_range(self, x_range, y, integ_range=None):
        """calculates an integrated total"""
        total = 0
        i = 0
        if not integ_range:
            integ_range = self.presentation.integ_lines
        for x in x_range:
            if integ_range[0] <= x <= integ_range[1]:
                total += y[i]
            i += 1
        return y + [total]

    def calculate_ypf(self, x_range, y, integ_range=None):
        """calculates an integrated total, ypf, ppf, and ppe"""
        if not y:
            return
        total = 0
        ypf = 0
        ppf = 0
        ppe_r = 0
        ppe_fr = 0
        i = 0
        if not integ_range:
            integ_range = self.presentation.integ_lines
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
            i += 1
        if ppe_r:
            ppe = ppe_r/(ppe_r + ppe_fr)
        else:
            ppe = 0.0
        return y + [total, ppf, ypf, ppe]

    def calculate_lux(self, data, device, fc = False):
        if not data: return
        y = []
        i = 0
        j = 0
        for x in device.x_data:
            x = int(x)
            y.append(0)
            if 380 <= x <= 780:
                y[-1] = LUX_MULTIPLIER * data[i] * CIE_1931[x - 380]
                if fc:
                    y[-1] = y[-1] * LUX_TO_FOOTCANDLES
            i += 1
        return y

    def get_reflectance_transmittance(self, device):
        """plots reflactance/transmittance as a percentage"""
        if device.change_units.is_set():
            try:
                device.irrad_unit = COUNTS
            except DeviceCommunicationError, data:
                evt = event_error(title="Connection Error", msg=data.message)
                PostEvent(self.presentation.frame, evt)
                return
            device.change_units.clear()
            self.presentation.label = r'$Percent$'
        return device.get_spectrum(rt=True)

    def remove_dark_scan_noise(self, data, device, mode):
        """this method subtracts the dark scan noise from the raw signal using a
        multiplier based on the integration time"""
        integ_multiplier = float(device.prev_integ)/device.dark_integ_list[mode]
        i = 0
        while len(data) > i < len(device.dark_ref_list[mode]):
            data[i] = data[i] - device.dark_ref_list[mode][i] * \
                (integ_multiplier)
            i += 1
        return data

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
        self.presentation.show_help_menu(tab)

    def set_dark_reference(self):
        """save a dark reference to attempt to cancel dark noise or for use with
        reflectance/transmittance"""
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        cont_play = False
        if self.active_threads:
            cont_play = True
        device = self.active_device
        mode = self.active_mode
        if not device:
            return
        msg = "Cover the sensor head to block all incident radiation, then\n" \
            " press 'OK' to save the dark reference."
        proceed = self.presentation.ok_cancel("Dark Reference", msg)
        if not proceed:
            return
        busy = self.presentation.busy("Taking Dark Reference Scan")
        try:
            data = device.get_pixel_data()
            device.dark_reference = [i - 1500 for i in data]
            device.dark_integ = device.prev_integ
        except DeviceCommunicationError, data:
            busy = None
            del(busy)
            evt = event_error(title="Connection Error", msg=data.message)
            PostEvent(self.presentation.frame, evt)
            return
        busy = None
        del(busy)
        self.presentation.clear_dark_ref.Enable()
        self.presentation.confirmation_message("Dark Reference Saved",
                                               "Success!")
        device.dark_ref_taken = True
        if cont_play:
            self.start_plot_threads()
        else:
            self.take_and_plot_snapshot()

    def set_light_reference(self):
        """save a light reference spectrum for reflectance/transmittance"""
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        cont_play = False
        if self.active_threads:
            msg = "You'll need to exit Continuous Measurement mode to take a " \
                "\nnew light reference. "
            self.presentation.confirmation_message("Light Reference", msg)
            return
        device = self.active_device
        if not device:
            return
        msg = "Illuminate the sensor head with reference lamp, then press \n" \
            "'OK' to save the light reference"
        proceed = self.presentation.ok_cancel("Light Reference", msg)
        if not proceed:
            return
        busy = self.presentation.busy("Taking Light Reference Scan")
        try:
            data = device.get_pixel_data()
            device.light_reference = [i - 1500 for i in data]
        except DeviceCommunicationError, data:
            busy = None
            del(busy)
            evt = event_error(title="Connection Error", msg=data.message)
            PostEvent(self.presentation.frame, evt)
            return
        busy = None
        del(busy)
        self.presentation.confirmation_message("Light Reference Saved",
                                               "Success!")

    def clear_dark_ref(self):
        """sets dark reference to null"""
        device = self.active_device
        if not device:
            return
        if not device.dark_reference:
            self.presentation.confirmation_message(
                "The active device does not have a saved dark scan.",
                "No Dark Reference")
            return
        else:
            device.dark_reference = []
            device.dark_ref_taken = False
        self.presentation.confirmation_message(
            "Dark Reference has been removed", "Success!")

    def copy_plot_to_clipboard(self):
        """copys the plot area to the system clipboard as an image"""
        self.presentation.copy_plot_to_clipboard(gettempdir())
        msg = "Your image has been copied to the system clipboard"
        self.presentation.confirmation_message(msg, "Success!")

    def compute_derivative(self, data):
        """performs a very rudimentary numerical derivative of the data set.
        because our steps in the x axis are one, no division is necessary"""
        i = 1
        derivative = []
        while i < self.abstraction.x_data_range[1] - self.abstraction.x_data_range[0] + 1:
            derivative.append((data[i] - data[i-1]))
            i += 1
        derivative.append(0.0)
        return derivative

    def compute_and_plot_first_derivative(self):
        """computes derivative and plots the outcome"""
        if not self.abstraction.y_data:
            msg = "Please take a reading before attempting this function.\n"
            self.presentation.give_error("No Scan Data", msg)
            return
        first_derivative = self.compute_derivative(self.abstraction.y_data[0])
        self.presentation.plot_signal(first_derivative, "First Derivative")

    def compute_and_plot_second_derivative(self):
        """computes the derivative twice and plots the outcome"""
        if not self.abstraction.y_data:
            msg = "Please take a reading before attempting this function.\n"
            self.presentation.give_error("No Scan Data", msg)
            return
        first_derivative = self.compute_derivative(self.abstraction.y_data[0])
        second_derivative = self.compute_derivative(first_derivative)
        self.presentation.plot_signal(second_derivative, "Second Derivative")

    def update_integration_time(self):
        """lets the thread know a new user specified integration time needs to
        be set"""
        self.abstraction.integ_time = self.presentation.integ_time
        for device in self.devices:
            device.update_integ.set()

    def set_auto_integration(self, auto_on):
        """resets the device to auto-integration and lets the thread know a new
        integration time needs to be set"""
        self.abstraction.auto_integrate = auto_on
        for device in self.devices:
            device.update_integ.set()
        self.presentation.integration_time.Enable(not auto_on)
        if not auto_on:
            if self.abstraction.connected:
                self.presentation.integration_time.SetValue(
                    self.active_device.prev_integ/1000)
                self.abstraction.integ_time = self.active_device.prev_integ

    def set_auto_scale(self, auto_on):
        self.presentation.set_auto_scale(not auto_on)

    def update_number_of_scans_to_average(self):
        """lets the thread know a new number of average scans needs to be set"""
        self.abstraction.average_scans = self.presentation.average_scans
        for device in self.devices:
            device.update_average_scans.set()

    def update_mode_and_units(self):
        """since plot signal checks the graph mode before each plot, this method
        enables units and tells thread to update units"""
        self.presentation.enable_units()
        self.active_mode = self.presentation.active_mode
        self.active_unit = self.presentation.active_unit
        d = False
        for device in self.devices:
            device.change_units.set()
            if device.dark_ref_taken:
                if not device.dark_reference:
                    d = True
        if d:
            self.presentation.confirmation_message(
                "A new dark reference will need to be taken for this plot mode",
                "Warning")

    def validate_and_update_y_axis(self):
        """make sure miniminum value is less than maximum value and update
        presentation"""
        maxy = self.presentation.max_y
        miny = self.presentation.min_y
        if miny == '-' or maxy == '-':
            return
        if miny > maxy:
            self.presentation.set_background_color(
                self.presentation.y_axis_max, "Red")
            return
        try:
            float(miny)
            float(maxy)
        except ValueError:
            self.presentation.set_background_color(
                self.presentation.y_axis_max, "Red")
            return
        if miny == maxy:
            maxy += 0.01
        self.presentation.y_axis_limits = (miny, maxy)
        self.presentation.set_background_color(
            self.presentation.y_axis_max, "White")
        self.presentation.draw()

    def validate_and_update_x_axis(self):
        """make sure miniminum value is less than maximum value and update
        presentation"""
        maxx = self.presentation.max_x
        minx = self.presentation.min_x
        if minx == '-' or maxx == '-':
            return
        if minx > maxx:
            self.presentation.set_background_color(
                self.presentation.x_axis_max, "Red")
            return
        try:
            float(minx)
            float(maxx)
        except ValueError:
            self.presentation.set_background_color(
                self.presentation.y_axis_max, "Red")
            return
        self.presentation.x_axis_limits = (minx, maxx)
        self.presentation.set_background_color(
            self.presentation.x_axis_max, "White")
        self.presentation.draw()

    def reset_original_plot(self):
        """refresh the current plot with orginal zoom/axes settings"""
        if self.abstraction.multi_plot_data:
            self.presentation.refresh_plot_defaults(
                multi_plot=self.abstraction.multi_plot_data)
        else:
            self.presentation.refresh_plot_defaults(
                self.abstraction.x_data_range, self.abstraction.y_data)

    def toggle_average(self):
        """when plotting multiple lines, this method turns on and off the average
        plot"""
        self.presentation.toggle_average()

    def change_plot_view(self, mode, units):
        """this method handles the menu -> view selection and lets the thread know
        it needs to update"""
        self.stop_all_threads()
        self.presentation.active_mode = mode
        if units is not None:
            self.presentation.active_unit = units
        self.presentation.enable_units()
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
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        self.presentation.set_calibration_mode(len(self.devices),
                                               self.save_dark_pixels,
                                               self.clear_dark_pixels,
                                               self.light_reference_cal,
                                               self.device_reference_cal,
                                               self.dark_reference_cal,
                                               self.dark_ref_clear)

    def light_reference_cal(self, event):
        """gives user instruction on how to take calibration scan, takes the scan,
        and writes it to memory"""
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        msg = "Place the sensor under the calibration light and press OK to\n" \
            " take a Calibration Scan"
        cont = self.presentation.ok_cancel("Calibration Scan", msg)
        if not cont:
            return
        device = self.active_device
        if not device:
            return
        self.calibrate(device, LOCK_IN_CALIBRATION)

    def dark_reference_cal(self, event):
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        msg = "Cover the sensor head to block all incident radiation, then\n" \
            " press 'OK' to save the dark reference."
        cont = self.presentation.ok_cancel("Dark Reference", msg)
        if not cont:
            return
        device = self.active_device
        if not device:
            return
        self.calibrate(device, LOCK_IN_DARK_SCAN)

    def dark_ref_clear(self, event):
        device = self.active_device
        device.dark_ref_clear()

    def calibrate(self, device, lock_code):
        self.presentation.active_mode = RELATIVE
        self.presentation.enable_units()
        device.irrad_unit = COUNTS
        try:
            device.calibration_scan = device.get_spectrum()
        except DeviceCommunicationError, data:
            self.presentation.give_error("Connection Error", data.message)
            return
        self.presentation.plot_signal(device.calibration_scan,
                                      "Calibration Scan")
        self.presentation.integ_time = self.abstraction.integ_time = device.prev_integ
        msg = "Do you want to keep the current calibration scan?\n"
        cont = self.presentation.ok_cancel("Keep Scan?", msg)
        if not cont:
            return
        if lock_code == LOCK_IN_CALIBRATION:
            calibration_file = self.presentation.calibration_file_dialog(
                self.abstraction.current_directory)
            if not calibration_file:
                return
            calibration_data = self.parse_and_compute_calibration_data(
                calibration_file, device)
        else:
            calibration_data = device.calibration_scan
        msg = "Press okay to overwrite calibration data."
        cont = self.presentation.ok_cancel("Are you sure?!", msg)
        if not cont:
            return
        try:
            device.set_calibration_data(calibration_data, lock_code)
        except DeviceCommunicationError, data:
            self.presentation.give_error("Connection Error", data.message)
            return
        self.presentation.confirmation_message(
            "Calibration data has been saved", "Success!")

    def remove_dark_pixels(self, data, dark_pixels):
        """temporary method as this will eventually be taken care of in firmware.
        takes the good points before and after the dark pixel and overwrites the
        bad pixel with the midpoint between them bad pixel is the index of the bad
        pixel in data list"""
        for bad_pixel in dark_pixels:
            if bad_pixel == 0:
                a = 0
            else:
                a = data[int(bad_pixel) - 1]
            if bad_pixel == len(data) - 1:
                b = 0
            else:
                b = data[int(bad_pixel) + 1]
            data[int(bad_pixel)] = (a + b)/2
        return data

    def device_reference_cal(self, event):
        if not len(self.devices) >= 2:
            msg = "You need a minimum of 2 reference devices to use this " \
                "function."
            self.presentation.give_error("Calibration Error", msg)
            return
        msg = "Place the sensors under the calibration light and press OK to\n" \
            " take a Calibration Scan"
        cont = self.presentation.ok_cancel("Calibration Scan", msg)
        if not cont:
            return
        self.presentation.active_mode = RELATIVE
        self.presentation.enable_units()
        device = self.active_device
        for dev in self.devices:
            if dev == device:
                dev.irrad_unit = COUNTS
            else:
                dev.irrad_unit = MICRO_MOLES
            dev.change_units.clear()
            # we want at least a 5 scan average of all devices
            self.presentation.average_scans = 5
            self.abstraction.average_scans = 5
            dev.update_average_scans.set()
        for dev in self.devices:
            try:
                self.spectrum_snapshot(dev)
            except DeviceCommunicationError, data:
                self.presentation.give_error("Connection Error", data)
                return
        self.device_ref_cal_snapshot()
        if len(self.abstraction.multi_plot_data) != len(self.devices):
            # something went wrong somewhere
            return
        self.presentation.integ_time = self.abstraction.integ_time = device.prev_integ
        msg = "Do you want to keep the current calibration scan and write\n" \
            "calibration data to device: %s?" % device.name
        cont = self.presentation.ok_cancel("Keep Scan?", msg)
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
            self.presentation.give_error("Connection Error", data)
        self.presentation.confirmation_message(
            "Calibration data has been saved", "Success!")

    def device_ref_cal_snapshot(self):
        self.presentation.show_average_button.SetValue(False)
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
        self.abstraction.multi_plot_data = plot_data
        self.presentation.plot_multiline(self.abstraction.multi_plot_data,
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
        calibration_factors = []
        i = int(device.x_data[0]) - 280
        for counts in device.calibration_scan:
            factor = lamp_output[i]/counts
            calibration_factors.append(factor)
            i += 1
        return calibration_factors

    def save_dark_pixels(self, event):
        """saves/appends the currently selected dark_pixels"""
        device = self.active_device
        for marker in self.presentation.markers:
            if marker not in device.dark_pixels:
                device.dark_pixels.append(float(marker))
        device.dark_pixels.sort()
        self.presentation.markers = []
        try:
            device.set_bad_pixel_data()
        except DeviceCommunicationError, data:
            self.presentation.give_error("Connection Error", data.message)
        else:
            self.presentation.confirmation_message(
                "Calibration data has been saved", "Success!")
            self.presentation.draw()

    def clear_dark_pixels(self, event):
        device = self.active_device
        device.clear_dark_pixels()

    def take_and_plot_snapshot(self):
        """takes a single measurement and plots it to the screen"""
        self.stop_all_threads()
        #print sys.getrefcount(None)
        if not self.abstraction.connected:
            self.connect_to_device()
            if not self.abstraction.connected:
                return
        self.presentation.show_average_button.SetValue(False)
        self.abstraction.multi_plot_data = []
        self.abstraction.y_data = []
        if self.presentation.active_mode == RT:
            for device in self.devices:
                if not (device.light_reference and device.dark_reference):
                    msg = "Please take a Dark and Light Reference point for %s" \
                        "\n before attempting to plot Reflectance/Transmittance"
                    self.presentation.give_error("No Light/Dark Reverence",
                                                 msg % device.name)
                    return
        self.presentation.current_process("Plotting Snapshot")
        busy = self.presentation.busy("Taking a measurement...")
        change_units = True
        if len(self.devices) > 1:
            if change_units is not True:
                self.wait()
            self.take_multi_device_snapshot()
            self.presentation.integ_time = self.abstraction.integ_time = self.active_device.prev_integ
            self.presentation.current_process("")
            busy = None
            del(busy)
            return
        device = self.active_device
        if not device:
            self.presentation.current_process("")
            return
        try:
            #print sys.getrefcount(None)
            y = self.get_active_signal_data(device)
        except DeviceCommunicationError, data:
            self.presentation.current_process("")
            self.presentation.give_error("Connection Error", data.message)
            return
        if not y:
            self.presentation.current_process("")
            return
        self.abstraction.y_data = [y]
        self.presentation.plot_signal(y, device.name)
        self.presentation.integ_time = self.abstraction.integ_time = device.prev_integ
        self.presentation.current_process("")
        del(y)
        busy = None
        del(busy)
        gc.collect()

    def take_multi_device_snapshot(self):
        plot_data = []
        for device in self.devices:
            try:
                scan_data = {}
                scan_data['x_data'] = device.x_data
                scan_data['labels'] = [device.name]
                y = self.get_active_signal_data(device)
                # we will continue here instead of return in the case of one device
                # failing but the other's do not. software will still plot the data
                # from the devices who do not fail
                if not y:
                    continue
                scan_data['y_data'] = [y]
                plot_data.append(scan_data)
            except DeviceCommunicationError, data:
                self.presentation.give_error("Connection Error", data.message)
        self.abstraction.multi_plot_data = plot_data
        self.presentation.plot_multiline(self.abstraction.multi_plot_data,
                                         average=False)

    def update_vlines(self):
        self.presentation.update_vlines()

    # close apogee spectrovision
    def shutdown_application(self):
        self.presentation.frame.Close()

    def stop_all_threads(self):
        self.presentation.current_process("")
        self.start_thread.clear()
        self.stop_thread.set()
        self.active_threads = []

    def pause_all_threads(self):
        self.presentation.current_process("Paused...")
        self.pause_thread.set()

    def right_click_menu(self, event):
        self.old_name = event.GetEventObject().GetLabel()
        self.presentation.pop_up_menu(self.process_choice)

    def process_choice(self, event):
        choice = event.GetId()
        if choice == 0:
            name = self.presentation.rename_device(self.old_name)
            if not name:
                name = self.old_name
            for device in self.devices:
                if device.name == self.old_name:
                    device.name = name
                    device.set_device_alias(name)
            for sensor in self.presentation.sensors:
                if sensor.GetLabel() == self.old_name:
                    sensor.SetLabel(name)
                    sensor.Fit()
                    sensor.Refresh()
            self.old_name = None
            del(self.old_name)
            self.presentation.tool_bar.Realize()
        elif choice == 1:
            self.stop_all_threads()
            for device in self.devices:
                if device.name == self.old_name:
                    device.disconnect_spec()
                    self.presentation.remove_device(device.name)
                    self.devices.remove(device)
                    self.abstraction.connected_serials.remove(device.dev.serial_number[2:6])
                    break
            if not self.devices:
                self.abstraction.connected = False
            if len(self.devices) == 1:
                self.presentation.x_data = self.devices[0].x_data
            self.old_name = None
            del(self.old_name)

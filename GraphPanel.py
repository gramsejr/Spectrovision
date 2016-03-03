# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from math import ceil
import sys
import gc

import wx
import wx.lib.newevent
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg, \
     NavigationToolbar2Wx
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor, Button

from constants import IS_MAC, LUX, FOOTCANDLE, RQE, SIGMA_R, SIGMA_FR, \
     CIE_1931, LUX_TO_FOOTCANDLES, PHOTON_FLUX, LUX_MULTIPLIER, ENERGY_FLUX, \
     ILLUMINANCE, X_LABEL

custom_event, CUSTOM_EVT = wx.lib.newevent.NewEvent()


class GraphPanel(wx.Panel):
    def __init__(self, parent, frame):
        super(GraphPanel, self).__init__(parent, -1)
        self.SetBackgroundColour((218,238,255))
        self.SetWindowStyle(wx.RAISED_BORDER)
        self.parent = parent
        self.frame = frame
        self.figure = Figure()
        self.figure.set_facecolor(color='#daeeff')
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.axes = self.figure.add_subplot(111)
        self.axes.legend(loc=1)
        self.x_data = range(340, 821)
        self.y_data = [0] * 481
        self.color_map = self.wavelength_to_rgb()
        self.axes.plot(self.x_data, self.y_data, label='Scan 1')
        self.canvas = FigureCanvasWxAgg(self, -1, self.figure)
        self.figure.tight_layout()
        self.sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL)
        self.sizer.AddSpacer(20)
        self.add_toolbar()
        self.SetSizer(self.sizer)
        self.figure.canvas.draw()
        self.cid1 = self.figure.canvas.mpl_connect('motion_notify_event',
                                                   self.on_movement)
        self.cid2 = self.figure.canvas.mpl_connect('button_press_event',
                                                   self.on_press)
        self.cid3 = self.figure.canvas.mpl_connect('scroll_event',
                                                   self.on_scroll)
        self.cursor = Cursor(self.axes, useblit=True, color='black',
                             linewidth=1)
        self.units = ''
        self.calibrate_mode = False
        self.integ_lines = []
        self.plot_unit = -1
        self.plot_mode = -1
        self.text = None

    def re_init(self):
        self.frame = frame
        self.figure = Figure()
        self.figure.set_facecolor(color='#daeeff')
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasWxAgg(self, -1, self.figure)
        self.figure.tight_layout()
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL)
        self.sizer.AddSpacer(20)
        self.SetSizer(self.sizer)
        self.cid1 = self.figure.canvas.mpl_connect('motion_notify_event',
                                                   self.on_movement)
        self.cid2 = self.figure.canvas.mpl_connect('button_press_event',
                                                   self.on_press)
        self.cid3 = self.figure.canvas.mpl_connect('scroll_event',
                                                   self.on_scroll)
        self.cursor = Cursor(self.axes, useblit=True, color='black',
                             linewidth=1)

    @property
    def x_axis_limits(self):
        return self.axes.get_xlim()

    @x_axis_limits.setter
    def x_axis_limits(self, new_axis_limits):
        self.axes.set_xlim((new_axis_limits))

    @property
    def y_axis_limits(self):
        return self.axes.get_ylim()

    @y_axis_limits.setter
    def y_axis_limits(self, new_axis_limits):
        self.axes.set_ylim((new_axis_limits))
        if self.integ_lines:
            self.axes.vlines(self.integ_lines, new_axis_limits[0],
                             new_axis_limits[1], colors='r')

    @property
    def x_label(self):
        return self.axes.get_xlabel()

    @x_label.setter
    def x_label(self, new_label):
        self.axes.set_xlabel(new_label)

    @property
    def y_label(self):
        return self.axes.get_ylabel()

    @y_label.setter
    def y_label(self, new_label):
        self.units = new_label
        self.axes.set_ylabel(new_label)

    def on_pixel_picker(self, event):
        """handles on click event when in calibration mode. selects data points.
        right click to remove selection"""
        mouseevent = event.mouseevent
        line = self.axes.get_lines()[0]
        try:
            index = list(line.get_xdata()).index(round(mouseevent.xdata))
        except ValueError:
            return
        if mouseevent.button is not 1:
            try:
                self.markers.remove(index)
            except ValueError:
                pass
            line.set_markevery(self.markers)
            self.figure.canvas.draw()
            return
        if index in self.markers:
            self.figure.canvas.draw()
            return
        self.markers.append(index)
        self.markers.sort()
        line.set_marker('o')
        line.set_markevery(self.markers)
        self.figure.canvas.draw()

    def add_toolbar(self):
        """adds the pan and zoom tools (and a few others) to a toolbar at the
        base of the plot panel"""
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        tw, th = self.toolbar.GetSizeTuple()
        fw, fh = self.canvas.GetSizeTuple()
        self.toolbar.SetSize(wx.Size(fw, th))
        # delete subplots and save image tools
        if IS_MAC:
            pass
        else:
            self.toolbar.DeleteToolByPos(8)
            self.toolbar.DeleteToolByPos(7)
        self.toolbar.SetBackgroundColour("white")
        self.sizer.Add(self.toolbar, 0, wx.EXPAND | wx.BOTTOM | wx.ALL, 0)
        self.toolbar.update()

    def on_movement(self, event):
        """displays cursor coordinates in the status bar. wx.PostEvent throws an
        interrupt that is caught in ASPresentation class frame"""
        try:
            if not event.xdata:
                return
            x = round(event.xdata)
            y = event.ydata
            coords = '(%d, %.2f)' % (x, y)
            evt = custom_event(coords=coords)
            wx.PostEvent(self.frame, evt)
        except Exception:
            pass

    def on_press(self, event):
        """handles button click during non-calibration mode. display box with y
        value text and x value along x axis. right click to remove box"""
        if not event.xdata:
            return
        while self.axes.texts:
            for text in self.axes.texts:
                text.remove()
        if self.text:
            if self.integ_lines:
                self.axes.texts.append(self.text)
            else:
                self.text = None
        if event.button is not 1:
            self.figure.canvas.draw()
            return
        x = round(event.xdata)
        try:
            text_lists = []
            ymin, ymax = self.axes.get_ylim()
            spacer = (ymax - ymin) * 0.03
            for line in self.axes.get_lines():
                try:
                    index = list(line.get_xdata()).index(x)
                except ValueError:
                    continue
                if line.get_label().startswith('_'):
                    continue
                y = list(line.get_ydata())[index]
                while(abs(y) - spacer < 0):
                    if y >= 0:
                        y += spacer/5
                    else:
                        y -= spacer/5
                text = line.get_label() + ': %.2f'
                text = text % y
                color = line.get_color()
                text_lists.append([x, y, text, color])
            text_lists.sort(key=lambda x: x[1])
            for i in range(len(text_lists) - 1):
                if text_lists[i][1] > text_lists[i+1][1]:
                    text_lists[i+1][1] = text_lists[i][1]
                while(abs(text_lists[i][1] - text_lists[i+1][1]) < spacer):
                    text_lists[i+1][1] += spacer/5
            for t in text_lists:
                self.axes.text(t[0], t[1] , t[2],
                               bbox={'facecolor': t[3],
                                     'alpha': 0.5, 'pad': 10})
                self.axes.text(t[0], 0, unicode(t[0]))
            self.figure.canvas.draw()
        except (ValueError, IndexError):
            pass

    def on_scroll(self, event):
        """on scroll in the plot window will zoom in if rolled forward or out if
        rolled back at a rate of .5% of total panel limits per wheel step"""
        if not event.step:
            return
        line = self.axes.get_lines()[0]
        xdata = line.get_xdata()
        ydata = line.get_ydata()
        center_x = xdata[len(xdata)/2]
        center_y = ydata[len(ydata)/2]
        steps = event.step
        limits = self.x_axis_limits
        minx = limits[0]
        maxx = limits[1]
        limits = self.y_axis_limits
        miny = limits[0]
        maxy = limits[1]
        minx += minx * 0.005 * steps
        maxx -= maxx * 0.005 * steps
        if miny < 0:
            miny += miny * 0.005 * -steps
        else:
            miny += miny * 0.005 * steps
        maxy -= maxy * 0.005 * steps
        if minx > center_x:
            minx = center_x
        if maxx < center_x:
            maxx = center_x + 1
        if miny > center_y:
            miny = center_y
        if maxy < center_y:
            maxy = center_y + 1
        if not maxx - minx <=1:
            self.x_axis_limits = (minx, maxx)
        if not maxy - miny <=1:
            self.y_axis_limits = (miny, maxy)
        self.figure.canvas.draw()

    def plot_signal(self, y_data, auto_scale, color_map, label):
        """plots a single line with auto_scale and color_map as optional
        settings"""
        try:
            line = self.axes.get_lines()[0]
        except Exception:
            line, = self.axes.plot(self.x_data, new_y[:len(self.x_data)])
        #self.axes.clear()
        while self.axes.texts:
            for text in self.axes.texts:
                text.remove()
        if self.integ_lines:
            self.show_irradiance_data(auto_scale)
        if color_map:
            i = 0
            for x in self.x_data:
                if i >= len(self.x_data) - 1:
                    continue
                self.axes.fill_between([x, x + 1],
                                       [y_data[i], y_data[i+1]],
                                       color=self.color_map[int(x)-340])
                i += 1
        try:
            line.set_data(self.x_data, y_data[:len(self.x_data)])
            line.set_label(label)
        except ValueError:
            # plot units were updated before new data could be calculated
            # dont plot this round
            pass
        if self.calibrate_mode:
            line.set_picker(True)
            line.set_marker('o')
            line.set_markevery(self.markers)
        if auto_scale:
            self.axes.relim(visible_only=True)
            self.axes.autoscale_view(scalex=False)
        self.figure.canvas.draw()
        try:
            wx.YieldIfNeeded()
        except Exception:
            pass
        return self.axes.get_xlim(), self.axes.get_ylim()

    def plot_multiline(self, scan_data, average, auto_scale, active_device=None):
        """plots multiple line data from data capture or from file. auto scale
        is always on but limits can be adjusted from the left panel in the 
        application. Color mapping is disabled for multiline plots. Also
        computes and plots the average of all lines plotted. The average line
        can be disabled with a button in the left panel"""
        self.axes.clear()
        self.axes.set_xlabel(X_LABEL)
        average_scan= {}
        self.axes.autoscale(auto_scale)
        x_data_set = set()
        total_scans = 0
        for data in scan_data:
            try:
                if data['labels'][0] == active_device:
                    if len(data['y_data']) == 1:
                        self.y_data = data['y_data'][0]
                        if self.integ_lines:
                            self.show_irradiance_data(auto_scale)
            except Exception:
                pass
            x_data = data['x_data']
            for scan in data['y_data']:
                i = 0
                for x in x_data:
                    # using a set here and building x_data manually to handle
                    # possible multiplot averages with different wavelength
                    # ranges
                    if x not in x_data_set:
                        x_data_set.add(x)
                        average_scan[unicode(x)] = [0,0]
                    average_scan[unicode(x)][0] += scan[i]
                    average_scan[unicode(x)][1] += 1
                    i += 1
            i = 0
            for scan in data['y_data']:
                self.axes.plot(x_data, scan[:len(x_data)],
                               label=data['labels'][i])
                total_scans += 1
                i += 1
        if average:
            avg = sorted(map(lambda x: float(x), average_scan.keys()))
            avg_x = []
            avg_y = []
            for i in range(len(average_scan)):
                avg_y.append(average_scan[unicode(avg[i])][0]/ \
                             average_scan[unicode(avg[i])][1])
                avg_x.append(int(avg[i]))
            self.axes.plot(avg_x, avg_y, label='Average', color='black',
                           linewidth=3)
        self.axes.legend(loc=1)
        self.figure.canvas.draw()
        return self.axes.get_xlim(), self.axes.get_ylim()

    def show_irradiance_data(self, auto_scale):
        if self.plot_mode == PHOTON_FLUX:
            total, ppf, ypf, ppe = self.y_data[-4:]
            self.apply_text(
                "Integrated Total: %0.4f\nPPF: %.4f\nYPF: %.4f\nPPE: %.4f"
                % (total, ppf, ypf, ppe))
        elif self.plot_mode == ENERGY_FLUX:
            total = self.y_data[-1]
            self.apply_text("Integrated Total: %0.4f" % total)
        elif self.plot_mode == ILLUMINANCE:
            total = self.y_data[-1]
            if self.plot_unit == LUX:
                self.apply_text("LUX: %.4f" % total)
            elif self.plot_unit == FOOTCANDLE:
                self.apply_text("Footcandle: %.4f" % total)
        if auto_scale:
            ma = max(self.y_data[:-20])
            mi = min(self.y_data[:-20])
            self.y_axis_limits = (mi * 1.05, ma * 1.05)
        y_lim = self.axes.get_ylim()
        self.axes.vlines(self.integ_lines, y_lim[0], y_lim[1], colors='r')

    def apply_text(self, text):
        self.text = self.axes.text(0.01, 0.99, text, size='x-large',
                                   verticalalignment='top',
                                   horizontalalignment='left',
                                   transform=self.axes.transAxes)

    def toggle_average(self):
        """turns on and off the average line. used only in multi-plot
        instances"""
        for line in self.axes.get_lines():
            if line.get_label() == 'Average':
                line.set_visible(False)
                line.set_label('_Average')
            elif line.get_label() == '_Average':
                line.set_visible(True)
                line.set_label('Average')
        while self.axes.texts:
            for text in self.axes.texts:
                text.remove()
        self.axes.legend(loc=1)
        self.figure.canvas.draw()

    def save_graph(self, file_path):
        """saves the current plot as a user specified image type"""
        self.figure.savefig(file_path)

    def wavelength_to_rgb(self, gamma=1.0):
        """computes the color mapping rgb values where 0 <= r, g, b <= 1."""
        color_map = []
        for wavelength in range(340, 1101):
            wavelength = float(wavelength)
            if wavelength >= 340 and wavelength <=370:
                R = 0.0
                G = 0.0
                B = 0.0
            elif wavelength >= 370 and wavelength <= 460:
                attenuation = (wavelength - 340) / (460 - 340)
                R = ((-(wavelength - 460) / (460 - 340)) * attenuation) ** gamma
                G = 0.0
                B = (1.0 * attenuation) ** gamma
            elif wavelength >= 460 and wavelength <= 500:
                R = 0.0
                G = (0.9 * (wavelength - 460) / (500 - 460)) ** gamma
                B = 1.0 ** gamma
            elif wavelength >= 500 and wavelength <= 530:
                R = 0.0
                G = 0.9 ** gamma
                B = (-(wavelength - 530) / (530 - 500)) ** gamma
            elif wavelength >= 530 and wavelength <= 580:
                R = ((wavelength - 530) / (580 - 530)) ** gamma
                G = 0.9 + (0.1 * (wavelength - 530) / (580 - 530)) ** gamma
                B = 0.0
            elif wavelength >= 580 and wavelength <= 640:
                R = 1.0 ** gamma
                G = (-(wavelength - 640) / (640 - 580)) ** gamma
                B = 0.0
            elif wavelength >=640 and wavelength <=680:
                R = 1.0 ** gamma
                G = 0.0
                B = 0.0
            elif wavelength >= 680 and wavelength <= 740:
                attenuation = (740 - wavelength) / (740 - 680)
                R = (attenuation) ** gamma
                G = 0.0
                B = 0.0
            elif wavelength >= 740 and wavelength <=800:
                attenuation = (-(wavelength - 800 )) / (800 - 740)
                R = 0.8 - (0.8 * attenuation) ** gamma
                G = 0.8 - (0.8 * attenuation) ** gamma
                B = 0.8 - (0.8 * attenuation) ** gamma
            else:
                attenuation = (-(wavelength - 1100 )) / (1100 - 800)
                R = (0.8 * attenuation) ** gamma
                G = (0.8 * attenuation) ** gamma
                B = (0.8 * attenuation) ** gamma
            color_map.append((R, G, B))
        return color_map

    def set_calibration_mode(self):
        """enables pixel picking for calibration mode. this method works as a
        toggle. a second call of this method will turn off pixel picking and
        reenable orignal on-click settings"""
        if not self.calibrate_mode:
            self.figure.canvas.mpl_disconnect(self.cid2)
            for line in self.axes.get_lines():
                line.set_picker(True)
            self.cid2 = self.figure.canvas.mpl_connect(
                'pick_event', self.on_pixel_picker)
            self.markers = []
            self.calibrate_mode = True
            return
        self.figure.canvas.mpl_disconnect(self.cid2)
        self.cid2 = self.figure.canvas.mpl_connect('button_press_event',
                                                   self.on_press)
        self.markers = []
        self.calibrate_mode = False

    def vlines(self, enable, integ_range):
        """displays, updates, and removes integration range lines for Irradiance
        mode"""
        if enable:
            self.integ_lines = integ_range
        else:
            self.integ_lines = []

    def draw(self):
        self.figure.canvas.draw()

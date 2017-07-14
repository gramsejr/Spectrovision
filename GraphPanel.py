# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import wx
import wx.lib.newevent
import matplotlib
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg, \
     NavigationToolbar2WxAgg
from matplotlib.figure import Figure
from matplotlib.widgets import Cursor

from constants import IS_MAC, LUX, FOOTCANDLE, RQE, SIGMA_R, SIGMA_FR, \
     CIE_1931, LUX_TO_FOOTCANDLES, PHOTON_FLUX, LUX_MULTIPLIER, ENERGY_FLUX, \
     ILLUMINANCE, X_LABEL

matplotlib.rcParams['mathtext.default'] = 'regular'

custom_event, CUSTOM_EVT = wx.lib.newevent.NewEvent()

def add_toolbar(sizer, canvas):
    """adds the pan and zoom tools (and a few others) to a toolbar at the
    base of the plot panel"""
    toolbar = NavigationToolbar2WxAgg(canvas)
    toolbar.Realize()
    tw, th = toolbar.GetSizeTuple()
    fw, fh = canvas.GetSizeTuple()
    toolbar.SetSize(wx.Size(fw, th))
    # delete subplots and save image tools
    if IS_MAC:
        pass
    else:
        toolbar.DeleteToolByPos(8)
        toolbar.DeleteToolByPos(7)
    toolbar.SetBackgroundColour("white")
    sizer.Add(toolbar, 0, wx.EXPAND | wx.BOTTOM | wx.ALL, 0)
    toolbar.update()

def wavelength_to_rgb(gamma=1.0):
    """computes the color mapping rgb values where 0 <= r, g, b <= 1."""
    color_map = []
    for wavelength in range(340, 1101):
        wavelength = float(wavelength)
        if wavelength >= 340 and wavelength <=370:
            R = 0.0
            G = 0.0
            B = 0.0
        elif wavelength >= 370 and wavelength <= 460:
            attenuation = (wavelength - 370) / (460 - 370)
            R = ((-(wavelength - 460) / (460 - 370)) * attenuation) ** gamma
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

COLOR_MAP = wavelength_to_rgb()

class GraphPanel(wx.Panel):
    def __init__(self, parent, red_farred):
        super(GraphPanel, self).__init__(parent, -1)
        self.SetBackgroundColour((218,238,255))
        self.SetWindowStyle(wx.RAISED_BORDER)
        figure = Figure()
        figure.set_facecolor(color='#daeeff')
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.axes = figure.add_subplot(111)
        self.x_data = range(340, 821)
        self.axes.plot(self.x_data, [0] * 481, label='Scan 0')
        self.axes.legend(loc=1)
        self.canvas = FigureCanvasWxAgg(self, -1, figure)
        figure.tight_layout(pad=2.0)
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL)
        sizer.AddSpacer(20)
        add_toolbar(sizer, self.canvas)
        self.SetSizer(sizer)
        self.canvas.draw()
        cid1 = self.canvas.mpl_connect('motion_notify_event', self.on_movement)
        cid2 = self.canvas.mpl_connect('button_press_event', self.on_press)
        cid3 = self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.integ_lines = []
        self.fractional_lines = []
        self.plot_unit = -1
        self.plot_mode = -1
        self.text = None
        self.x_label = X_LABEL
        self.red_farred = red_farred

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
        if self.integ_lines and self.plot_mode != ILLUMINANCE:
            self.axes.vlines(self.integ_lines, new_axis_limits[0],
                             new_axis_limits[1], colors='r')
            self.axes.vlines(self.fractional_lines, new_axis_limits[0],
                             new_axis_limits[1], colors='black')

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
        self.axes.set_ylabel(new_label)

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
            wx.PostEvent(self.Parent.Parent, evt)
        except Exception:
            pass

    def get_selected_wavelength(self, active_device):
        for line in self.axes.lines:
            if line.get_label() == active_device.name:
                try:
                    index = line.get_markevery()[0]
                except IndexError:
                    #nothing selected
                    return None
                else:
                    return line.get_xdata()[index]

    def on_press(self, event):
        """handles button click during non-calibration mode. display box with y
        value text and x value along x axis. right click to remove box"""
        if not event.xdata:
            return
        # clear revious text boxes
        while self.axes.texts:
            for text in self.axes.texts:
                text.remove()
        # if it was right click or middle click, just leave text boxes removed
        if event.button is not 1:
            for line in self.axes.get_lines():
                line.set_markevery([])
            if self.text:
                # leave integration data on plot
                if self.integ_lines:
                    self.axes.text(0.01, 0.99, self.text.get_text(),
                                   size='x-large',
                                   verticalalignment='top',
                                   horizontalalignment='left',
                                   transform=self.axes.transAxes)
            self.canvas.draw()
            return
        x = round(event.xdata)
        text_lists = []
        ymin, ymax = self.axes.get_ylim()
        xmin, xmax = self.axes.get_xlim()
        # spacer is 3% of window size
        spacer = (ymax - ymin) * 0.03
        xspacer = (xmax - xmin) * 0.005
        try:
            for line in self.axes.get_lines():
                try:
                    # make sure line has data where mouse was clicked
                    index = list(line.get_xdata()).index(x)
                except ValueError:
                    continue
                # if label starts with '_' we don't display it. this is what lets
                # us show and hide the average line and label
                if line.get_label().startswith('_'):
                    continue
                # get y coordinate corresponding to the x value
                y = list(line.get_ydata())[index]
                while(abs(y) - spacer < 0):
                    if y >= 0:
                        y += spacer/5
                    else:
                        y -= spacer/5
                text = line.get_label() + ': (%s, %.2f)'
                text = text % (int(x), y)
                color = line.get_color()
                text_lists.append([x, y, text, color])
                line.set_marker('o')
                line.set_markevery([index])
            text_lists.sort(key=lambda x: x[1])
            for i in range(len(text_lists) - 1):
                if text_lists[i][1] > text_lists[i+1][1]:
                    text_lists[i+1][1] = text_lists[i][1]
                while(abs(text_lists[i][1] - text_lists[i+1][1]) < spacer):
                    text_lists[i+1][1] += spacer/5
            for t in text_lists:
                self.axes.text(t[0] + xspacer, t[1] + spacer, t[2],
                               bbox={'facecolor': t[3],
                                     'alpha': 0.25, 'pad': 5})
            if self.text:
                if self.integ_lines:
                    self.axes.text(0.01, 0.99, self.text.get_text(),
                                   size='x-large',
                                   verticalalignment='top',
                                   horizontalalignment='left',
                                   transform=self.axes.transAxes)
                else:
                    self.text = None
            self.canvas.draw()
        except (ValueError, IndexError):
            pass

    def on_scroll(self, event):
        """on scroll in the plot window will zoom in if rolled forward or out if
        rolled back at a rate of .5% of total panel limits per wheel step"""
        if not event.step:
            return
        try:
            line = self.axes.get_lines()[0]
        except IndexError:
            return
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
        self.canvas.draw()

    def plot_signal(self, y_data, auto_scale, color_map, label):
        """plots a single line with auto_scale and color_map as optional
        settings"""
        try:
            self.axes.lines = [self.axes.lines[0]]
            line = self.axes.lines[0]
            line.set_markevery([])
        except Exception:
            line, = self.axes.plot(self.x_data, y_data[:len(self.x_data)])
        else:
            line.set_data(self.x_data, y_data[:len(self.x_data)])
        self.axes.collections = [] # removes any leftover integration lines
        self.axes.texts = [] # clears out any texts
        line.set_label(label)
        self.axes.legend(loc=1)
        if self.integ_lines:
            self.show_irradiance_data(y_data, auto_scale)
        if color_map:
            self.add_rainbow(y_data)
        if auto_scale:
            self.axes.relim(visible_only=True)
            self.axes.autoscale_view(scalex=False)
        self.axes.autoscale(enable=auto_scale)
        self.canvas.draw()
        try:
            wx.YieldIfNeeded()
        except Exception:
            pass
        return self.axes.get_xlim(), self.axes.get_ylim()

    def plot_multiline(self, scan_data, average, auto_scale, active_device=None,
                       paired=[]):
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
        if paired: # and self.plot_mode in[ENERGY_FLUX, PHOTON_FLUX]:
            #combine paired sensors into single line
            new_scan_data = []
            for p in paired:
                new_dict = {}
                new_dict['labels'] = [p[0] + ' and ' + p[1]]
                new_dict['x_data'] = range(340, 1101)
                new_dict['y_data'] = [[0] * 761]
                scans = scan_data[:]
                for data in scans:
                    if data['labels'][0] not in p:
                        continue
                    y = data['y_data'][0]
                    i = data['x_data'][0] - 340
                    j = 0
                    while i <= data['x_data'][-1] - 340:
                        if new_dict['y_data'][0][i] == 0:
                            new_dict['y_data'][0][i] = y[j]
                        else:
                            new_dict['y_data'][0][i] = (y[j] + new_dict['y_data'][0][i])/2
                        i += 1
                        j += 1
                    scan_data.remove(data)
                if active_device in new_dict['labels'][0]:
                    if self.plot_mode == PHOTON_FLUX:
                        new_dict['y_data'][0] = self.calculate_ypf(new_dict['x_data'], new_dict['y_data'][0])
                    elif self.plot_mode in [ENERGY_FLUX, ILLUMINANCE]:
                        new_dict['y_data'][0] = self.integrate_range(new_dict['x_data'], new_dict['y_data'][0])
                        if self.plot_mode == ILLUMINANCE:
                            del(new_dict['y_data'][0][-2:])
                new_scan_data.append(new_dict)
            for data in scan_data:
                new_scan_data.append(data)
            scan_data = new_scan_data
        for data in scan_data:
            try:
                if self.integ_lines:
                    if active_device in data['labels'][0] or active_device == 'None':
                        self.show_irradiance_data(data['y_data'][0],
                                                  auto_scale)
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
                        average_scan[x] = [0,0]
                    average_scan[x][0] += scan[i]
                    average_scan[x][1] += 1
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
                avg_y.append(average_scan[avg[i]][0]/ \
                             average_scan[avg[i]][1])
                avg_x.append(int(avg[i]))
            self.axes.plot(avg_x, avg_y, label='Average', color='black',
                           linewidth=2)
        self.axes.legend(loc=1)
        self.canvas.draw()
        return self.axes.get_xlim(), self.axes.get_ylim()

    def show_irradiance_data(self, y_data, auto_scale):
        if self.plot_mode == PHOTON_FLUX:
            total, ppf, ypf, ppe, fract, r_rf = y_data[-6:]
            self.apply_text(
                "Integrated Total: %0.4f\nFraction of Total: %0.4f" \
                "\nPPF: %.4f\nYPF: %.4f\nPPE: %.4f\nR/FR: %.4f"
                % (total, fract, ppf, ypf, ppe, r_rf))
        elif self.plot_mode == ENERGY_FLUX:
            total, fract, r_rf = y_data[-3:]
            self.apply_text("Integrated Total: %0.4f\nFraction of Total: %0.4f" \
                            "\nR/FR: %.4f" % (total, fract, r_rf))
        elif self.plot_mode == ILLUMINANCE:
            total = y_data[-1]
            if self.plot_unit == LUX:
                self.apply_text("LUX: %.4f" % total)
            elif self.plot_unit == FOOTCANDLE:
                self.apply_text("Footcandle: %.4f" % total)
        ma = max(y_data[:-20])
        mi = min(y_data[:-20])
        if ma == mi:
            mi -= 0.001
            ma += 0.001
        mi *= 1.05
        ma *= 1.05
        if auto_scale:
                self.y_axis_limits = (mi , ma)
        elif self.plot_mode != ILLUMINANCE:
            self.axes.vlines(self.integ_lines, mi, ma, colors='r')
            self.axes.vlines(self.fractional_lines, mi, ma, colors='black')

    def add_rainbow(self, y_data):
        i = 0
        for x in self.x_data:
            if i >= len(self.x_data) - 1:
                continue
            self.axes.fill_between([x, x + 1],
                                   [y_data[i], y_data[i+1]],
                                   color=COLOR_MAP[x-340])
            i += 1

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
        self.axes.texts = []
        if self.text:
            if self.integ_lines:
                self.axes.text(0.01, 0.99, self.text.get_text(),
                               size='x-large',
                               verticalalignment='top',
                               horizontalalignment='left',
                               transform=self.axes.transAxes)
            else:
                self.text = None
        self.axes.legend(loc=1)
        self.canvas.draw()

    def save_graph(self, file_path):
        """saves the current plot as a user specified image type"""
        self.canvas.figure.savefig(file_path)

    def vlines(self, enable, integ_range, fractional_range):
        """displays, updates, and removes integration range lines for Irradiance
        mode"""
        if enable:
            self.integ_lines = integ_range
            self.fractional_lines = fractional_range
        else:
            self.integ_lines = []
            self.fractional_lines = []

    def draw(self):
        self.canvas.draw()

    def integrate_range(self, x_range, y):
        """calculates an integrated total"""
        total = fraction = i = r = fr = 0
        integ_range = self.integ_lines
        fractional_range = self.fractional_lines
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
        integ_range = self.integ_lines
        fractional_range = self.fractional_lines
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

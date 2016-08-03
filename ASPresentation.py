# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import time
import os
import sys

import wx
from wx.lib.buttons import GenBitmapTextToggleButton
from wx.lib.scrolledpanel import ScrolledPanel
import wx.lib.masked as masked

from constants import VERSION, IS_GTK, IS_WIN, IS_MAC, RELATIVE, PHOTON_FLUX, \
     RT, ENERGY_FLUX, LUX, FOOTCANDLE, ILLUMINANCE, WX_WM2_LABEL, \
     WX_MICROMOL_LABEL, WX_LUX_LABEL, WX_FC_LABEL, LEFTPANEL_HELP, MENUBAR_HELP, \
     TOOLBAR_HELP, PLOTVIEW_HELP, ABOUT_TEXT, SERVICED
from ASControl import EVT_ERROR, PLOT_EVT, STATUS_EVT, TOOLBAR_EVT
from GraphPanel import GraphPanel, CUSTOM_EVT
from Messages import ok_cancel, give_error, confirmation_message, time_control, \
     progress_dialog, save_file_dialog, open_file_dialog

def resource_path(relative):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative)

def dead_object_catcher(func):
    def func_wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except wx.PyDeadObjectError:
            pass
        return ret
    return func_wrapper

class ASPresentation(object):
    def __init__(self):
        """the ASPresentation class contains all the display components of the 
        application and handles all the calls to the gui, some of which
        are rerouted to the GraphPanel class in GraphPanel.py"""
        title = 'Apogee SpectroVision - Version %s' % VERSION
        self.frame = wx.Frame(None, -1, title=title, size=(1280, 800))
        self.frame.SetBackgroundColour("white")
        self.sensors = []
        self.calibrate_mode = False
        # set the application icon
        if IS_MAC:
            img_src = resource_path('image_source/%s')
            icon = wx.Icon(img_src % 'apogee-icon-256.png',
                           wx.BITMAP_TYPE_PNG)
            tb_icon = wx.TaskBarIcon(iconType=wx.TBI_DOCK)
            tb_icon.SetIcon(icon, "Apogee Spectrovision")
        elif IS_WIN:
            img_src = 'image_source\\%s'
            icon = wx.Icon(img_src % "apogee-icon-256.png")
        elif IS_GTK:
            img_src = 'image_source/%s'
            icon = wx.Icon(img_src % 'apogee-icon-256.png',
                           wx.BITMAP_TYPE_PNG)
        self.frame.SetIcon(icon)

        # split frame into 3 parts: top, left, and graph windows
        self.vertical_splitter = wx.SplitterWindow(self.frame, -1)
        self.vertical_splitter.SetBackgroundColour("white")
        self.vertical_splitter.SetWindowStyle(wx.RAISED_BORDER)
        self.horizontal_splitter = wx.SplitterWindow(self.vertical_splitter, -1)
        self.bottom_left_panel = wx.Panel(self.horizontal_splitter, -1)
        self.bottom_left_panel.SetBackgroundColour("white")
        self.bottom_left_panel.SetWindowStyle(wx.RAISED_BORDER)
        self.bottom_left_panel.SetMaxSize((250, 75))
        self.left_panel = ScrolledPanel(self.horizontal_splitter, -1)
        self.left_panel.SetBackgroundColour((218,238,255))
        self.left_panel.SetWindowStyle(wx.RAISED_BORDER)
        self.graph_panel = GraphPanel(self.vertical_splitter)
        self.horizontal_splitter.SetMinimumPaneSize(60)
        self.horizontal_splitter.SplitHorizontally(self.left_panel, self.bottom_left_panel, -60)
        self.vertical_splitter.SetMinimumPaneSize(25)
        self.vertical_splitter.SplitVertically(self.horizontal_splitter,
                                               self.graph_panel, 160)

        apogee_logo = wx.StaticBitmap(
            self.bottom_left_panel, -1, wx.Bitmap(img_src % "ApogeeLogo.png"),
            size=(150, -1))
        sizer = wx.BoxSizer()
        sizer.Add(apogee_logo, 0, wx.ALIGN_CENTER | wx.ALL, 0)
        self.bottom_left_panel.SetSizer(sizer)

        # set up menu bar
        menu_bar = wx.MenuBar()
        self.file_menu = wx.Menu()
        self.file_menu.Append(100, "&Data Capture", "Setup a data capture scheme")
        self.file_menu.Append(101, "&Connect", "Connect to a device")
        self.file_menu.Append(102, "D&isconnect", "Disconnect a device")
        self.file_menu.Append(103, "&Red/Far Red Setup")
        self.file_menu.Enable(102, False)
        self.file_menu.AppendSeparator()
        self.file_menu.Append(wx.ID_EXIT, "&Exit")
        menu_bar.Append(self.file_menu, "&File")

        view_menu = wx.Menu()
        view_menu.Append(200, "&Raw Signal", "Plot relative data")
        view_menu.Append(201, "Reflectance/&Transmittance",
                         "Plot reflectance/transmittance")
        view_menu.Append(203, "&Energy Flux Density",
                         "Plot in calibrated unit %s" % WX_WM2_LABEL)
        view_menu.Append(202, "&Photon Flux Density",
                         "Plot in calibrated unit %s" % WX_MICROMOL_LABEL)
        submenu = wx.Menu()
        submenu.Append(204, "&Lux",
                       "Plot in calibrated unit Lux: %s" % WX_LUX_LABEL)
        submenu.Append(205, "&Footcandle",
                       "Plot in calibrated unit Footcandle: %s" % WX_FC_LABEL)
        view_menu.AppendMenu(211, "&Illuminance", submenu)
        menu_bar.Append(view_menu, "&View")

        help_menu = wx.Menu()
        help_menu.Append(300, "&Left Panel", "Get help with Left Panel controls")
        help_menu.Append(301, "&MenuBar", "Get help with MenuBar options")
        help_menu.Append(302, "&Toolbar", "Get help with ToolBar controls")
        help_menu.Append(303, "&Plot Area", "Get help with plot area controls")
        help_menu.AppendSeparator()
        help_menu.Append(304, "&About Apogee SpectroVision",
                         "Learn about Apogee SpectroVision")
        menu_bar.Append(help_menu, "&Help")
        menu_bar.SetBackgroundColour("white")

        self.frame.SetMenuBar(menu_bar)

        # create a status bar.
        self.status_bar = wx.StatusBar(self.frame)
        self.status_bar.SetFieldsCount(4)
        self.status_bar.SetStatusWidths([-2, -1, -1, -1])
        self.frame.SetStatusBar(self.status_bar)
        self.status_bar.Font = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                                       wx.FONTSTYLE_NORMAL,
                                       wx.FONTWEIGHT_NORMAL)
        self.status_bar.SetBackgroundColour("white")

        self.tool_bar = wx.ToolBar(self.frame)
        self.tool_bar.SetToolBitmapSize((35,35))
        self.tool_bar.SetBackgroundColour("white")
        self.frame.SetToolBar(self.tool_bar)
        
        # crete controls for top frame
        # create bitmap buttons with tooltip ballons
        self.dark_reference = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'dark_ref.jpg'))
        tool_tip = wx.ToolTip("Set dark reference")
        self.dark_reference.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.dark_reference)

        self.light_reference = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'light_ref.jpg'))
        tool_tip = wx.ToolTip("Set light reference")
        self.light_reference.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.light_reference)

        self.clear_dark_ref = wx.BitmapButton(
            self.tool_bar, -1, 
            bitmap=wx.Bitmap(img_src % 'clear_dark_ref.jpg'))
        tool_tip = wx.ToolTip("Clear the current dark reference")
        self.clear_dark_ref.SetToolTip(tool_tip)
        self.clear_dark_ref.Disable()
        self.tool_bar.AddControl(self.clear_dark_ref)

        self.open_file = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'open_icon.jpg'))
        tool_tip = wx.ToolTip("Open a data file for plotting\n (Ctrl + o)")
        self.open_file.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.open_file)

        self.save_spectrum = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'save_icon.jpg'))
        tool_tip = wx.ToolTip("Save graph as image\n (Ctrl + s)")
        self.save_spectrum.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.save_spectrum)

        self.save_data = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'save_data_icon.jpg'))
        tool_tip = wx.ToolTip("Save graph data\n (Ctrl + d)")
        self.save_data.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.save_data)

        self.save_both = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'purp_save_icon.jpg'))
        tool_tip = wx.ToolTip("Save graph data and image\n (Ctrl + a)")
        self.save_both.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.save_both)

        self.copy_graph_image = wx.BitmapButton(
            self.tool_bar, -1,
            bitmap=wx.Bitmap(img_src % 'copy_graph_icon.jpg'))
        tool_tip = wx.ToolTip("Copy graph to clipboard\n (Ctrl + c)")
        self.copy_graph_image.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.copy_graph_image)

        self.first_derivative = wx.BitmapButton(
            self.tool_bar, -1,
            wx.Bitmap(img_src % 'first_derivative.jpg'))
        tool_tip = wx.ToolTip("Plot the first derivative")
        self.first_derivative.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.first_derivative)

        self.second_derivative = wx.BitmapButton(
            self.tool_bar, -1,
            wx.Bitmap(img_src % 'second_derivative.jpg'))
        tool_tip = wx.ToolTip("Plot the second derivative")
        self.second_derivative.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.second_derivative)

        self.snap_shot = wx.BitmapButton(
            self.tool_bar, -1, 
            wx.Bitmap(img_src % 'camera.jpg'))
        tool_tip = wx.ToolTip("Take a single measurement\n (F1)")
        self.snap_shot.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.snap_shot)

        self.play_button = wx.BitmapButton(
            self.tool_bar, -1,
            wx.Bitmap(img_src % 'play.jpg'))
        tool_tip = wx.ToolTip("Start continuous measurements\n (F2)")
        self.play_button.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.play_button)

        self.pause_button = wx.BitmapButton(
            self.tool_bar, -1,
            wx.Bitmap(img_src % 'pause.jpg'))
        tool_tip = wx.ToolTip("Pause continuous measurements\n (F3)")
        self.pause_button.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.pause_button)

        self.stop_button = wx.BitmapButton(
            self.tool_bar, -1,
            wx.Bitmap(img_src % 'stop.jpg'))
        tool_tip = wx.ToolTip("Stop continuous measurements\n (F4)")
        self.stop_button.SetToolTip(tool_tip)
        self.tool_bar.AddControl(self.stop_button)
        self.tool_bar.AddSeparator()
        self.tool_bar.Realize()

        # create controls for left panel
        # integration time controls
        integration_time_label = wx.StaticText(self.left_panel, -1,
                                               "Integration Time (ms)")
        self.integration_time = wx.SpinCtrl(
            self.left_panel, value='2000', min=5, max=10000, size=(120, -1),
            style=wx.TE_PROCESS_ENTER | wx.ALIGN_RIGHT)
        self.integration_time.Disable()
        self.auto_integration = wx.ToggleButton(
            self.left_panel, -1, "Auto-Integration", size=(120, 30))
        self.auto_integration.SetValue(True)
        number_of_scans_label = wx.StaticText(self.left_panel, -1,
                                              "Scans to Average")

        # average number of scans controls
        self.number_of_scans_to_avg = wx.SpinCtrl(
            self.left_panel, value='1', min=1, max=100, size=(120, -1))

        # graph mode and unit controls
        self.relative = wx.RadioButton(
            self.left_panel, label="Relative", style=wx.RB_GROUP)
        self.relative.SetValue(True)
        self.r_t = wx.RadioButton(
            self.left_panel, label="Refl./Trans.")

        self.energy_flux = wx.RadioButton(
            self.left_panel, label="Energy Flux Density")

        self.photon_flux = wx.RadioButton(
            self.left_panel, label="Photon Flux Density")

        self.illuminance = wx.RadioButton(self.left_panel, label="Illuminance")
        self.lux = wx.RadioButton(
            self.left_panel, label="Lux", style=wx.RB_GROUP)
        self.footcandle = wx.RadioButton(
            self.left_panel, label="Footcandle")

        # integration range spin controls
        integ_range = wx.StaticText(self.left_panel, -1, "Integration Range")
        self.integ_min = wx.SpinCtrl(self.left_panel, value="340", min=340,
                                     max=819, size=(60, -1),
                                     style=wx.TE_PROCESS_ENTER)
        self.integ_min.Disable()
        self.integ_max = wx.SpinCtrl(self.left_panel, value="820", min=341,
                                     max=820, size=(60, -1),
                                     style=wx.TE_PROCESS_ENTER)
        self.integ_max.Disable()

        fraction_range = wx.StaticText(self.left_panel, -1, "Fractional Range")
        self.fraction_min = wx.SpinCtrl(self.left_panel, value="340", min=340,
                                        max=819, size=(60, -1),
                                        style=wx.TE_PROCESS_ENTER)
        self.fraction_min.Disable()
        self.fraction_max = wx.SpinCtrl(self.left_panel, value="820", min=341,
                                        max=820, size=(60, -1),
                                        style=wx.TE_PROCESS_ENTER)
        self.fraction_max.Disable()

        # axes limits controls
        y_axes = wx.StaticText(self.left_panel, -1, "Y Axes Limits")
        self.y_axis_min = wx.SpinCtrlDouble(self.left_panel,  min=-16383,
                                            max=16382, size=(60, -1), inc=0.01,
                                            style=wx.TE_PROCESS_ENTER)
        self.y_axis_max = wx.SpinCtrlDouble(self.left_panel, min=-16382,
                                            max=16383, size=(60, -1), inc=0.01,
                                            style=wx.TE_PROCESS_ENTER)
        x_axes = wx.StaticText(self.left_panel, -1, "X Axes Limits")
        self.x_axis_min = wx.SpinCtrlDouble(self.left_panel, min=300, inc=0.01,
                                            max=1139, size=(60, -1),
                                            style=wx.TE_PROCESS_ENTER)
        self.x_axis_max = wx.SpinCtrlDouble(self.left_panel, min=301, inc=0.01,
                                            max=1140, size=(60, -1),
                                            style=wx.TE_PROCESS_ENTER)

        self.integration_time.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.number_of_scans_to_avg.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.integ_min.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.integ_max.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.fraction_min.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.fraction_max.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.y_axis_min.GetChildren()[0].Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.y_axis_max.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.x_axis_min.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        self.x_axis_max.Bind(wx.EVT_SET_FOCUS, self.number_pad)


        # toggle button plot options
        self.set_auto_scale(en=False)
        self.auto_scale_toggle = wx.ToggleButton(self.left_panel, -1,
                                                 "Auto Scale", size=(120, -1))
        self.auto_scale_toggle.SetValue(True)
        self.color_map_toggle = wx.ToggleButton(
            self.left_panel, -1, "Map Color Range", size=(120, -1))
        self.reset_button = wx.Button(self.left_panel, -1, label="Reset Plot",
                                      size=(120, -1))
        self.show_average_button = wx.ToggleButton(
            self.left_panel, -1, "Show Average", size=(120, -1))
        self.show_average_button.Disable()


        # all controls have been created. now its time to add them all to the 
        # sizers in a nice layout
        self.vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        self.vertical_sizer.Add(integration_time_label, 0,
                                wx.ALIGN_CENTER | wx.ALL)
        self.vertical_sizer.Add(self.integration_time, 0,
                                wx.ALIGN_CENTER | wx.ALL)
        self.vertical_sizer.Add(self.auto_integration, 0,
                                wx.ALIGN_CENTER | wx.ALL, 1)
        divider = wx.StaticLine(self.left_panel, -1)
        self.vertical_sizer.Add(divider, 0, wx.EXPAND | wx.ALL, border=5)

        self.vertical_sizer.Add(number_of_scans_label, 0,
                                wx.ALIGN_CENTER | wx.ALL)
        self.vertical_sizer.Add(self.number_of_scans_to_avg, 0,
                                wx.ALIGN_CENTER | wx.ALL)

        divider = wx.StaticLine(self.left_panel, -1)
        self.vertical_sizer.Add(divider, 0, wx.EXPAND | wx.ALL, border=5)

        self.vertical_sizer.Add(self.relative, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        self.vertical_sizer.Add(self.r_t, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        self.vertical_sizer.Add(self.energy_flux, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        self.vertical_sizer.Add(self.photon_flux, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        self.vertical_sizer.Add(self.illuminance, 0, wx.ALIGN_LEFT | wx.ALL, 2)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.AddSpacer(20)
        h_sizer.Add(self.lux, 0, wx.ALIGN_LEFT | wx.ALL)
        self.vertical_sizer.Add(h_sizer, 0, wx.ALIGN_LEFT | wx.ALL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.AddSpacer(20)
        h_sizer.Add(self.footcandle, 0, wx.ALIGN_LEFT | wx.ALL)
        self.vertical_sizer.Add(h_sizer, 0, wx.ALIGN_LEFT | wx.ALL)

        self.vertical_sizer.Add(integ_range, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        horizontal_sizer.Add(
            self.integ_min, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        horizontal_sizer.Add(
            self.integ_max, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        self.vertical_sizer.Add(
            horizontal_sizer, 0,  wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)

        self.vertical_sizer.Add(fraction_range, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        horizontal_sizer.Add(
            self.fraction_min, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        horizontal_sizer.Add(
            self.fraction_max, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        self.vertical_sizer.Add(
            horizontal_sizer, 0,  wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)

        divider = wx.StaticLine(self.left_panel, -1)
        self.vertical_sizer.Add(divider, 0, wx.EXPAND | wx.ALL, border=5)

        self.vertical_sizer.Add(y_axes, 0,
                                wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        horizontal_sizer.Add(self.y_axis_min, 0, wx.ALIGN_CENTER | wx.ALL)
        horizontal_sizer.Add(self.y_axis_max, 0, wx.ALIGN_CENTER | wx.ALL)
        self.vertical_sizer.Add(horizontal_sizer, 0,
                                wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        self.vertical_sizer.AddSpacer(5)

        self.vertical_sizer.Add(x_axes, 0,
                                wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        horizontal_sizer.Add(self.x_axis_min, 0, wx.ALIGN_CENTER | wx.ALL)
        horizontal_sizer.Add(self.x_axis_max, 0, wx.ALIGN_CENTER | wx.ALL)
        self.vertical_sizer.Add(horizontal_sizer, 0,
                                wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)

        divider = wx.StaticLine(self.left_panel, -1)
        self.vertical_sizer.Add(divider, 0, wx.EXPAND | wx.ALL, border=5)

        self.vertical_sizer.Add(
            self.auto_scale_toggle, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        self.vertical_sizer.Add(
            self.color_map_toggle, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        self.vertical_sizer.Add(self.reset_button, 0,
                                wx.ALIGN_CENTER | wx.ALL, 1)
        self.vertical_sizer.Add(
            self.show_average_button, 0, wx.ALIGN_CENTER | wx.ALL, 1)

        # set the sizer of the left panel
        self.left_panel.SetSizer(self.vertical_sizer)

        # i'm putting these binding here because I don't want to create a
        # workaround from GraphPanel.py -> ASInteraction.py -> ASControl.py ->
        # ASPresentation.py.
        # All other bindings are found in ASInteraction.py
        self.frame.Bind(CUSTOM_EVT, self.update_status_bar_coords)
        self.frame.Bind(EVT_ERROR, self.give_event_error)
        self.frame.Bind(PLOT_EVT, self.plot_event_data)
        self.frame.Bind(STATUS_EVT, self.status_bar_event)
        self.frame.Bind(TOOLBAR_EVT, self.enable_toolbar_controls)

        self.set_presented_limits(self.graph_panel.x_axis_limits,
                                  self.graph_panel.y_axis_limits)

        # show and maximize frame
        self.left_panel.SetupScrolling()
        self.frame.Show()
        self.frame.Maximize()

        self.enable_units()

    @property
    @dead_object_catcher
    def active_mode(self):
        """This property returns whichever plot mode is currently selected with
        the radio dials along the left panel."""
        if self.relative.GetValue():
            return RELATIVE
        if self.r_t.GetValue():
            return RT
        if self.photon_flux.GetValue():
            return PHOTON_FLUX
        if self.energy_flux.GetValue():
            return ENERGY_FLUX
        else:
            return ILLUMINANCE

    @active_mode.setter
    @dead_object_catcher
    def active_mode(self, mode):
        """Sets the active mode to the given value"""
        if mode == RELATIVE:
            self.relative.SetValue(True)
        if mode == RT:
            self.r_t.SetValue(True)
        if mode == PHOTON_FLUX:
            self.photon_flux.SetValue(True)
        if mode == ENERGY_FLUX:
            self.energy_flux.SetValue(True)
        if mode == ILLUMINANCE:
            self.illuminance.SetValue(True)

    @property
    @dead_object_catcher
    def active_unit(self):
        """returns either lux or footcandle and is only available in illuminance
        mode"""
        if  self.lux.IsEnabled():
            if self.lux.GetValue():
                return LUX
            return FOOTCANDLE
        return -1

    @active_unit.setter
    @dead_object_catcher
    def active_unit(self, new_unit):
        """sets the active unit to either lux or footcandle"""
        if new_unit == LUX:
            self.lux.SetValue(True)
        if new_unit == FOOTCANDLE:
            self.footcandle.SetValue(True)

    @property
    @dead_object_catcher
    def active_device(self):
        """returns which device is toggled in the toolbar"""
        for sensor in self.sensors:
            if sensor.GetValue():
                return sensor.GetLabel()

    @property
    def x_axis_limits(self):
        """returns the currently displayed x domain of the graph"""
        return self.graph_panel.x_axis_limits

    @x_axis_limits.setter
    def x_axis_limits(self, new_limits):
        """sets a new x domain for the displayed graph"""
        self.graph_panel.x_axis_limits = new_limits
        self.max_x = new_limits[1]
        self.min_x = new_limits[0]

    @property
    def y_axis_limits(self):
        """returns the currently displayed y range of the graph"""
        return self.graph_panel.y_axis_limits

    @y_axis_limits.setter
    def y_axis_limits(self, new_limits):
        """sets a new y range for the displayed graph"""
        self.graph_panel.y_axis_limits = new_limits
        self.max_y = new_limits[1]
        self.min_y = new_limits[0]

    @property
    def x_data(self):
        """returns the currently displayed x-values which is dependent on the
        device connected. It will be a list from 340-820, or from 635-1100. Both
        in increments of 1"""
        return self.graph_panel.x_data

    @x_data.setter
    def x_data(self, new_data):
        """sets a new list of x values"""
        self.graph_panel.x_data = new_data

    @property
    @dead_object_catcher
    def integ_time(self):
        """returns the integration displayed in the status bar. Only used when
        switching out of 'Auto-Integration' mode."""
        return self.integration_time.GetValue() * 1000.0

    @integ_time.setter
    @dead_object_catcher
    def integ_time(self, new_integ_time):
        """converts from integer in microseconds to float with 3 decimal places
        and displays new value in the status bar"""
        new_integ_time = float(new_integ_time)/1000000
        self.status_bar.SetStatusText(
            "Integration Time: %.3f s" % new_integ_time, 2)

    @property
    @dead_object_catcher
    def average_scans(self):
        """returns the number displayed in the 'Number of Scans to Average'
        spin control box"""
        return self.number_of_scans_to_avg.GetValue()

    @average_scans.setter
    @dead_object_catcher
    def average_scans(self, num):
        """sets a new number in the 'Number of Scans to Average' spin control"""
        self.number_of_scans_to_avg.SetValue(num)

    @property
    @dead_object_catcher
    def max_y(self):
        """returns the number displayed in the 'Y Max' spin control in the 'Axes
        Limits' section of the left panel"""
        return self.y_axis_max.GetValue()

    @max_y.setter
    @dead_object_catcher
    def max_y(self, new_max):
        """sets a new value to the 'Y Max' spin control box"""
        try:
            self.y_axis_max.SetValue(round(new_max, 3))
        except OverflowError:
            self.y_axis_max.SetValue(17000)

    @property
    @dead_object_catcher
    def min_y(self):
        """returns the number displayed in the 'Y Min' spin control box"""
        return self.y_axis_min.GetValue()

    @min_y.setter
    @dead_object_catcher
    def min_y(self, new_min):
        """sets a new value to the 'Y Min' spin control box"""
        try:
            self.y_axis_min.SetValue(round(new_min, 3))
        except OverflowError:
            self.y_axis_min.SetValue(-17000)

    @property
    @dead_object_catcher
    def max_x(self):
        """sets a new value to the 'X Max' spin control box"""
        return self.x_axis_max.GetValue()

    @max_x.setter
    @dead_object_catcher
    def max_x(self, new_max):
        """sets a new value to the 'X Max' spin control box"""
        self.x_axis_max.SetValue(round(new_max, 3))

    @property
    @dead_object_catcher
    def min_x(self):
        """sets a new value to the 'X Min' spin control box"""
        return self.x_axis_min.GetValue()

    @min_x.setter
    @dead_object_catcher
    def min_x(self, new_min):
        """sets a new value to the 'X Min' spin control box"""
        self.x_axis_min.SetValue(round(new_min, 3))

    @property
    def label(self):
        """returns the label currently displayed on the graph"""
        return self.graph_panel.y_label

    @label.setter
    def label(self, new_label):
        """sets a new label to be displayed on the graph"""
        self.graph_panel.y_label = new_label

    @property
    @dead_object_catcher
    def integ_lines(self):
        """returns the x values of the displayed integration range lines that
        are displayed during EFD and PFD modes"""
        return [self.integ_min.GetValue(), self.integ_max.GetValue()]

    @integ_lines.setter
    @dead_object_catcher
    def integ_lines(self, new_integ_range):
        """sets a new integration range on the plot"""
        self.integ_min.SetValue(new_integ_range[0])
        self.integ_max.SetValue(new_integ_range[1])

    @property
    @dead_object_catcher
    def fractional_lines(self):
        """returns the x values of the displayed integration range lines that
        are displayed during EFD and PFD modes"""
        return [self.fraction_min.GetValue(), self.fraction_max.GetValue()]

    @fractional_lines.setter
    @dead_object_catcher
    def fractional_lines(self, new_fractional_range):
        """sets a new integration range on the plot"""
        self.fraction_min.SetValue(new_fractional_range[0])
        self.fraction_max.SetValue(new_fractional_range[1])

    def enable_disconnect(self, enable=True):
        """enables/disables the disconnect option in the filemenu. This method
        is called with enable=True when a device has been connected and called
        with enable=False when there are no more devices connected"""
        self.file_menu.Enable(102, enable)

    
    def set_background_color(self, component, color):
        """generic set_background_color for the component passed. used when
        validating x and y axis limits"""
        component.SetBackgroundColour(color)

    def enable_integ_lines(self, enable=True, lm=False):
        """enables/disables the 'Integration Range' section of the left panel
        during EFT and PFD modes. If in Illuminance mode, the integration lines
        are still displayed and """
        self.integ_min.Enable(enable)
        self.integ_max.Enable(enable)
        self.fraction_min.Enable(enable)
        self.fraction_max.Enable(enable)
        if not lm:
            self.graph_panel.vlines(enable, self.integ_lines,
                                    self.fractional_lines)
        else:
            self.graph_panel.vlines(lm, self.integ_lines,
                                    self.fractional_lines)

    def enable_units(self):
        """depending on the mode and units selected with the radio controls in 
        the left panel, this method decides wether to enable or disable the
        integration lines and 'Integration Range' spin controls. Also sets
        the active mode and unit for the graph."""
        if self.active_mode == PHOTON_FLUX:
            self.integ_lines = [300, 800]
            self.enable_integ_lines()
        elif self.active_mode == ENERGY_FLUX:
            self.integ_lines = [340, 820]
            self.enable_integ_lines()
        elif self.active_mode == ILLUMINANCE:
            self.lux.Enable()
            self.footcandle.Enable()
            self.integ_lines = [380, 780]
            self.enable_integ_lines(False, lm=True)
            return
        else:
            self.enable_integ_lines(False)
        self.graph_panel.plot_mode = self.active_mode
        self.graph_panel.plot_unit = self.active_unit
        self.lux.Disable()
        self.footcandle.Disable()

    def update_status_bar_coords(self, event):
        """updates the status bar with the current mouse coordinates"""
        self.status_bar.SetStatusText(event.coords, 3)

    def status_bar_event(self, event):
        """updates the status bar integration time or current process. If the
        event has an attribute integ_time, the integration time is updated,
        otherwise the exception is caught and ignored and instead updates the
        current process. The event will never carry both sets of data. we use
        events so that the main thread is the only thread that touches the gui.
        bad things happen otherwise."""
        try:
            self.integ_time = event.integ_time
            return
        except AttributeError:
            pass
        self.current_process(event.status)

    def current_process(self, mode):
        """updates the status bar with the currently running process"""
        self.status_bar.SetStatusText(mode, 1)

    def open_data_file_dialog(self, current_directory):
        """prompts the user for a data file to open for plotting. can select
        multiple files so long as they are saved in the correct format."""
        wildcard = "(*.csv)|*.csv|(*.dat)|*.dat"
        dlg = wx.FileDialog(self.frame, "Open data file for plotting...",
                            current_directory, wildcard=wildcard,
                            style=wx.FD_OPEN | wx.FD_MULTIPLE)
        while dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            dlg.Destroy()
            return paths
        dlg.Destroy()

    def save_spectrum_dialog(self, current_directory, current_file):
        """returns the file path specified to save the graph image as a picture"""
        wildcard = "(*.jpg)|*.jpg|(*.png)|*.png|(*.pdf)|*.pdf|(*.ps)|*.ps|" \
            "(*.eps)|*.eps|(*.svg)|*.svg"
        title = "Save Spectrum As..."
        return save_file_dialog(self.frame, title, wildcard, current_directory, 
                               current_file)

    def save_data_dialog(self, current_directory, suggested_file=''):
        """returns the file path specified for saving the data file as either
        .dat or .csv"""
        wildcard = "(*.csv)|*.csv|(*.dat)|*.dat"
        title = "save data log as..."
        return save_file_dialog(self.frame, title, wildcard, current_directory, 
                               suggested_file, overwrite_prompt=False)

    def calibration_file_dialog(self, current_directory):
        """returns the file path of the chosen calibration file of type .icd"""
        wildcard="(*.icd)|*.icd"
        title = "Open Calibration File..."
        return open_file_dialog(self.frame, title, wildcard, current_directory)

    def gen_prog_dlg(self, title, msg, total):
        """generic progress dialog. this is used for the data caputre count
        down procedure because it can be closed automatically without input
        from the user. There is a bug in the wx.ProgressDialog that won't allow
        it to close properly."""
        return progress_dialog(title, msg, self.frame, total)

    def progress_dialog(self, settings, generator):
        """if total scans is zero, a gauge style dialog is used to indicate
        there is no defined end point. I think there might be a bug in this for
        windows xp users. every time I try to do continuous measurements on XP,
        it hangs for some reason. This may be the culprit. The main thread
        remains in this method and recieves it's data from a generator function
        in ASControl.py. Continually updates the progress dialog with returned
        value of the generator, checks if cancel button has been pushed, and
        repeats until generator has been terminated on the other end."""
        total_scans = settings['total_scans']
        if total_scans == 0:
            dlg = wx.ProgressDialog("Data Capture Progress",
                                    "Collecting Data",
                                    parent=self.frame,
                                    style=wx.PD_CAN_ABORT |
                                    wx.PD_APP_MODAL |
                                    wx.PD_ELAPSED_TIME |
                                    wx.PD_ESTIMATED_TIME)
        else:
            dlg = wx.ProgressDialog("Data Capture Progress",
                                    "Collecting Data",
                                    maximum=total_scans,
                                    parent=self.frame,
                                    style=wx.PD_CAN_ABORT |
                                    wx.PD_APP_MODAL |
                                    wx.PD_ELAPSED_TIME |
                                    wx.PD_ESTIMATED_TIME)
        for scan in generator(settings['total_scans'], settings['time_between_scans'],
                              settings['log_temperature'], self.active_mode,
                              self.active_unit):
            msg = "Collecting Data: %s" % scan
            if total_scans == 0:
                cont, skip = dlg.Pulse(msg)
            else:
                if scan > total_scans:
                    break
                msg += "/%s\n%.2f%% completed" % (
                    total_scans, float(scan)/total_scans * 100)
                if scan == total_scans:
                    continue
                cont, skip = dlg.Update(scan, msg)
            if not cont:
                dlg.Destroy()
                return False
        dlg.Destroy()
        return True

    def ok_cancel(self, title, msg):
        """generic query for a yes or no response"""
        return ok_cancel(self.frame, title, msg)

    def give_error(self, title, msg):
        """we don't want to accumulate a billion error messages of the same type
        so we wont display those that have the same title. Just need to make sure
        to pass unique titles so we can tell the difference between them."""
        for child in self.frame.GetChildren():
            if type(child) == wx._windows.Dialog:
                if child.GetTitle() == title:
                    child.Destroy()
        give_error(self.frame, title, msg)

    def give_event_error(self, event):
        """we raise and event to display our errors so that only the main thread
        attempts to update the gui. bad things happen otherwise."""
        self.give_error(event.title, event.msg)

    def save_graph(self, file_path):
        """saves the current plot has an image to the user specified file name"""
        self.graph_panel.save_graph(file_path)

    def connection_settings_query(self, previous, device_serials):
        """this is the connection settings dialog to get the slave_address and the
        com-port from the user. baud rate is hardcoded for now"""
        dlg = wx.Dialog(self.frame, -1, "Connection Settings")
        dlg.SetBackgroundColour("white")
        dlg.CenterOnScreen()
        serial_label = wx.StaticText(dlg, -1, "Choose the Device")
        serial = wx.ComboBox(dlg, -1, choices=device_serials)
        if previous in device_serials:
            serial.SetValue(previous)
        ok_button = wx.Button(dlg, wx.ID_OK)
        ok_button.SetFocus()
        cancel_button = wx.Button(dlg, wx.ID_CANCEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(serial_label, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(serial, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(ok_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        dlg.SetSizer(sizer)
        dlg.Fit()
        serial_num = None
        if dlg.ShowModal() == wx.ID_OK:
            serial_num = serial.GetValue()
        dlg.Destroy()
        return serial_num

    def disconnect_dialog(self, current_devices):
        """the disconnect dialog displays a combox box (drop down menu) of 
        currently connected spectroradiometers. this method displays the dialog
        and returns the string of the selected device"""
        dlg = wx.Dialog(self.frame, -1, "Disconnect Device")
        dlg.SetBackgroundColour("white")
        dlg.CenterOnScreen()
        text = wx.StaticText(dlg, -1, "Choose the device to disconnect")
        combo_box = wx.ComboBox(dlg, choices=current_devices)
        combo_box.SetValue(current_devices[0])
        ok_button = wx.Button(dlg, wx.ID_OK)
        ok_button.SetFocus()
        cancel_button = wx.Button(dlg, wx.ID_CANCEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(combo_box, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(ok_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        dlg.SetSizer(sizer)
        dlg.Fit()
        if dlg.ShowModal() == wx.ID_OK:
            device = combo_box.GetValue()
            dlg.Destroy()
            return device
        dlg.Destroy()

    # this is the data capture settings dialog displayed to the user on
    # startup of the data_capture function
    def data_capture_settings_dlg(self):
        """this is the data caputre settings dialog. when the user hits okay,
        the entered settings are then saved in a dictionary and returned to be
        interpreted by ASControl.py"""
        dlg = wx.Dialog(self.frame, -1, "Data-Capture Settings")
        dlg.CenterOnScreen()
        dlg.SetBackgroundColour("white")
        number_o_scans_text = wx.StaticText(
            dlg, -1, "Number of scans\n(if left at zero," \
            " number of scans will be continuous)", style=wx.ALIGN_CENTER)
        number_of_scans = wx.SpinCtrl(dlg, value='0', min=0, max=5000,
                                      size=(60, -1))
        time_between_text = wx.StaticText(
            dlg, -1, "Time between scans\n(if left at zero, scans will " \
            "be immediate)", style=wx.ALIGN_CENTER)
        minutes_text = wx.StaticText(dlg, -1, "Minutes", style=wx.ALIGN_CENTER)
        minutes = wx.SpinCtrl(dlg, value='0', min=0, max=50000,
                              size=(60, -1))
        seconds_text = wx.StaticText(dlg, -1, "Seconds", style=wx.ALIGN_CENTER)
        seconds = wx.SpinCtrl(dlg, value='0', min=0, max=60,
                              size=(60, -1))
        log_temperature = wx.CheckBox(dlg, label="Log Sensor Temperature")
        log_temperature.SetValue(False)
        save_to_file = wx.CheckBox(dlg, label="Save data to file")
        save_to_file.SetValue(True)
        plot_to_screen = wx.CheckBox(dlg, label="Plot data to screen")
        plot_to_screen.SetValue(False)
        set_start_time = wx.CheckBox(dlg, label="Use start time")
        start_time_text = wx.StaticText(dlg, -1, "Enter Start Time (24-hour)")
        curr_time = datetime.datetime.strftime(datetime.datetime.now(), "%H:%M:%S")
        time24 = masked.TimeCtrl(dlg, -1, curr_time, fmt24hr=True)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(number_o_scans_text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(number_of_scans, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(time_between_text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(minutes_text, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        v_sizer.Add(minutes, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        h_sizer.Add(v_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(seconds_text, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        v_sizer.Add(seconds, 0, wx.ALIGN_CENTER | wx.ALL, 1)
        h_sizer.Add(v_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(h_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(log_temperature, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(save_to_file, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(plot_to_screen, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(set_start_time, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(start_time_text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(time24, 0, wx.ALIGN_CENTER | wx.ALL, 0)
        sizer.Add(h_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(wx.Button(dlg, wx.ID_OK), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(wx.Button(dlg, wx.ID_CANCEL), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        dlg.SetSizer(sizer)
        dlg.Fit()
        settings = {}
        if dlg.ShowModal() == wx.ID_OK:
            settings['total_scans'] = number_of_scans.GetValue()
            settings['time_between_scans'] = minutes.GetValue() * 60 \
                + seconds.GetValue()
            settings['save_to_file'] = save_to_file.GetValue()
            settings['plot_to_screen'] = plot_to_screen.GetValue()
            settings['log_temperature'] = log_temperature.GetValue()
            if set_start_time.GetValue():
                settings['start_time'] = time24.GetValue(as_mxDateTime=True)
            else:
                settings['start_time'] = None
        dlg.Destroy()
        return settings

    def set_plot_settings(self, single_plot=True):
        """the name is ambiguous. this method is used to easily toggle between
        single and multi-sensor/multi-line plot settings."""
        self.enable_derivative(single_plot)
        self.show_average_button.Enable(not single_plot)
        self.color_map_toggle.Enable(single_plot)

    def plot_signal(self, new_y, label=''):
        """sets plot settings to single line, updates plot mode and unit,
        gathers auto-scale, color-mapping and x and y limits, passes them all to 
        the graph panel to plotted with the correct settings."""
        self.set_plot_settings(single_plot=True)
        self.graph_panel.plot_unit = self.active_unit
        self.graph_panel.plot_mode = self.active_mode
        auto_scale = self.auto_scale_toggle.GetValue()
        color_map = self.color_map_toggle.GetValue()
        x_lim, y_lim = self.graph_panel.plot_signal(
            new_y, auto_scale, color_map, label)
        if auto_scale:
            self.set_presented_limits(x_lim, y_lim)

    def plot_multiline(self, plot_data, average=True, active_device=None,
                       paired=[]):
        """esentialy the exact same thing as above but plots a multi-line graph
        for use with multiple sensors or when plotting from a file."""
        self.set_plot_settings(single_plot=False)
        self.graph_panel.plot_unit = self.active_unit
        self.graph_panel.plot_mode = self.active_mode
        self.show_average_button.SetValue(average)
        auto_scale = self.auto_scale_toggle.GetValue()
        if self.active_mode not in [ENERGY_FLUX, ILLUMINANCE, PHOTON_FLUX]:
            paired = []
        x_lim, y_lim = self.graph_panel.plot_multiline(
            plot_data, average, auto_scale, active_device, paired)
        if auto_scale:
            self.set_presented_limits(x_lim, y_lim)

    def plot_event_data(self, event):
        """just like the other events in here, this one is used so that only
        the main thread access the gui. works similar to status bar event in that
        it takes advantage of exceptions to determine which type of event we have
        and then plots accordingly"""
        try:
            if event.multiline:
                self.plot_multiline( event.plot_data, event.average,
                                     self.active_device, event.paired)
                return
        except AttributeError:
            pass
        self.plot_signal(event.plot_data, event.label)

    def set_presented_limits(self, x_lim, y_lim):
        """updates min and max axis values without resetting the plot setings"""
        self.max_x = x_lim[1]
        self.min_x = x_lim[0]
        self.max_y = y_lim[1]
        self.min_y = y_lim[0]

    # replots the current data and resets the x and y axis min and max
    def refresh_plot_defaults(self, x_data_range=[], y_data=[], multi_plot=[]):
        """this method is used to replot the current graph data using a relative
        zoom range and/or to update auto-scale and map-color range selections."""
        self.graph_panel.plot_mode = self.active_mode
        self.graph_panel.plot_unit = self.active_unit
        if not (y_data or multi_plot):
            msg = "Please take a reading before attempting this function.\n"
            self.give_error("No Scan Data", msg)
            return
        if self.active_mode == RT:
            self.y_axis_limits = (-25, 125)
        elif self.active_mode == RELATIVE:
            self.y_axis_limits = (-50, 16383)
        if not multi_plot:
            self.set_plot_settings(single_plot=True)
            self.x_axis_limits = (x_data_range[0], x_data_range[1])
            x_lim, y_lim = self.graph_panel.plot_signal(
                y_data[0], self.auto_scale_toggle.GetValue(),
                self.color_map_toggle.GetValue(), label='Scan 1')
        else:
            self.set_plot_settings(single_plot=False)
            x_min = 1100
            x_max = 340
            for scan in multi_plot:
                x_min = min(x_min, scan['x_data'][0])
                x_max = max(x_max, scan['x_data'][-1])
            self.x_axis_limits = (x_min, x_max)
            x_lim, y_lim = self.graph_panel.plot_multiline(
                multi_plot, self.show_average_button.GetValue(),
                self.auto_scale_toggle.GetValue(), str(self.active_device))
        self.set_presented_limits(x_lim, y_lim)
        self.graph_panel.Refresh()
        self.frame.Refresh()

    
    def enable_derivative(self, enable=True):
        """ enables and disables the derivative buttons. these are disabled for
        multiplot data"""
        self.first_derivative.Enable(enable)
        self.second_derivative.Enable(enable)


    def copy_plot_to_clipboard(self, directory):
        """copies the current plot image to the system clipboard.the image can
        then be pasted into other applications"""
        file_name = 'graph_image_copy.png'
        self.graph_panel.save_graph(os.path.join(directory, file_name))
        image_object = wx.BitmapDataObject(
            wx.Bitmap(os.path.join(directory, file_name)))
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(image_object)
            wx.TheClipboard.Close()
        else:
            wx.MessageBox("Unable to open the clipboard", "Error")

    def toggle_average(self):
        """turns on and off the plotting of the average line in multipline data"""
        self.graph_panel.toggle_average()

    def busy(self, msg):
        """generic busy box is displayed duriing sensitive processes (connecting and
        such) to prevent user from clicking buttons when it's hazardous to do so"""
        return wx.BusyInfo(msg, self.frame)

    def set_calibration_mode(self, number_of_sensors, light_ref_cal,
                             device_ref_cal):
        """this method adds or removes the calibration controls to/from the left
        panel. it is only activated using the ctrl-f10 hot key and should never
        be seen by customers."""
        self.calibrate_mode = not self.calibrate_mode
        if self.calibrate_mode:
            if not hasattr(self, "light_ref_cal"):
                self.calib_text = wx.StaticText(self.left_panel, -1,
                                                "Calibration Controls")
                self.light_ref_cal = wx.Button(
                    self.left_panel, -1, label="Light Reference Calibration",
                    size=(160, 35))
                self.device_ref_cal = wx.Button(
                    self.left_panel, -1, label="Device Reference Calibration",
                    size=(160, 35))
                self.vertical_sizer.Add(wx.StaticLine(self.left_panel, -1), 0,
                                        wx.EXPAND, 5)
                self.vertical_sizer.Add(self.calib_text, 0,
                                        wx.ALIGN_CENTER | wx.ALL, 8)
                self.vertical_sizer.Add(self.light_ref_cal, 0,
                                        wx.ALIGN_CENTER | wx.ALL, 1)
                self.vertical_sizer.Add(self.device_ref_cal, 0,
                                        wx.ALIGN_CENTER | wx.ALL, 1)
                self.frame.Bind(wx.EVT_BUTTON, light_ref_cal, self.light_ref_cal)
                self.frame.Bind(wx.EVT_BUTTON, device_ref_cal, self.device_ref_cal)
            else:
                self.vertical_sizer.Show(30)
                self.vertical_sizer.Show(31)
                self.vertical_sizer.Show(32)
                self.vertical_sizer.Show(33)
        else:
            self.vertical_sizer.Hide(30)
            self.vertical_sizer.Hide(31)
            self.vertical_sizer.Hide(32)
            self.vertical_sizer.Hide(33)
        self.vertical_sizer.RecalcSizes()
        self.vertical_sizer.Layout()
        self.left_panel.SetSizer(self.vertical_sizer)
        self.left_panel.FitInside()
        self.frame.Layout()

    def confirmation_message(self, title, msg):
        """comfirmation message shown to give the user the satisfaction of knowing
        something happened when they clicked a button"""
        confirmation_message(title, msg)

    def update_vlines(self):
        """updates the positions of the red integration range indicators on the
        raph"""
        self.graph_panel.integ_lines = [self.integ_min.GetValue(),
                                        self.integ_max.GetValue()]
        self.graph_panel.fractional_lines = [self.fraction_min.GetValue(),
                                             self.fraction_max.GetValue()]
        self.draw()

    def draw(self):
        """tells the graph to redraw itself"""
        self.graph_panel.draw()

    def add_sensor_to_toolbar(self, device_name, right_click_menu):
        """each time a sensor is connected, this method is called to add a 
        toggle control botton to the toolbar with the id of the sensors slave
        address. This allows it to be easly found and removed when the sensor
        is disconnected. the new sensor is automatically toggled as the active
        device"""
        if not IS_WIN:
            image_path = 'image_source/sensor.jpg'
        else:
            image_path = 'image_source\\sensor.jpg'
        sensor_toggle = GenBitmapTextToggleButton(
            self.tool_bar, -1, bitmap=wx.Bitmap(image_path),
            label=device_name, style=wx.LEFT)
        sensor_toggle.Bind(wx.EVT_RIGHT_DOWN, right_click_menu)
        self.frame.Bind(wx.EVT_BUTTON, self.on_device_toggle, sensor_toggle)
        self.sensors.append(sensor_toggle)
        self.on_device_toggle(button=sensor_toggle)
        self.tool_bar.AddControl(sensor_toggle)
        sensor_toggle.Fit()
        self.tool_bar.Realize()

    def pop_up_menu(self, handler, can_pair, paired):
        """this is a popup menu that is displayed when you right-click on a 
        device toggle button. it allows you to rename or disconnect the device
        easily"""
        menu = wx.Menu()
        menu.Append(0, "Rename")
        menu.Append(1, "Disconnect")
        menu.Append(4, "Reset")
        if can_pair:
            menu.Append(2, "Pair VIS with NIR")
        if paired:
            menu.Append(3, "Unpair Sensors")
        if self.calibrate_mode:
            menu.Append(5, "Set Device Serial")
        self.frame.Bind(wx.EVT_MENU, handler, id=0)
        self.frame.Bind(wx.EVT_MENU, handler, id=1)
        self.frame.Bind(wx.EVT_MENU, handler, id=2)
        self.frame.Bind(wx.EVT_MENU, handler, id=3)
        self.frame.Bind(wx.EVT_MENU, handler, id=4)
        self.frame.Bind(wx.EVT_MENU, handler, id=5)
        self.frame.PopupMenu(menu)
        menu.Destroy()

    def on_device_toggle(self, event=None, button=None):
        """because there is no bitmap toggle radio toolbar control combo
        (go figure right), I made my own! this method allows the sensor toggle 
        buttons to behave as radio buttons in that only one may be active at any
        given time.""" 
        if event:
            button = event.GetEventObject()
        for sensor in self.sensors:
            if sensor.GetId() == button.GetId():
                sensor.SetValue(True)
            else:
                sensor.SetValue(False)

    def remove_device(self, dev_name):
        """removes the toggle button with the name == dev_name. it requires
        that no devices are connected with the same name. In practice
        this should never happen anyway but I ran into problems with it during
        testing."""
        device_toggle = self.tool_bar.FindWindowByLabel(dev_name)
        self.sensors.remove(device_toggle)
        active = False
        for sensor in self.sensors:
            if sensor.GetValue():
                active = True
        if not active:
            if self.sensors:
                self.sensors[0].SetValue(True)
        self.tool_bar.DeleteTool(device_toggle.GetId())
        self.tool_bar.Realize()

    def rename_device(self, old_name):
        """renames the device to pretty much whatever the user wants to name
        their device."""
        dlg = wx.Dialog(self.frame, -1, "Rename")
        dlg.SetBackgroundColour("white")
        text = wx.StaticText(dlg, -1, "Rename device '%s' to:" % old_name)
        new_name = wx.TextCtrl(dlg, -1, old_name)
        new_name.SetMaxLength(16)
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(wx.Button(dlg, wx.ID_OK), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(wx.Button(dlg, wx.ID_CANCEL), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(new_name, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.CenterOnScreen()
        name = ""
        if dlg.ShowModal() == wx.ID_OK:
            name = new_name.GetValue()
        dlg.Destroy()
        return name

    def reserialize_device(self, old_serial):
        """reserializes the device to pretty much whatever we want to to."""
        dlg = wx.Dialog(self.frame, -1, "Set Serial")
        dlg.SetBackgroundColour("white")
        text = wx.StaticText(dlg, -1, "Change device serial from '%s' to:" % old_serial)
        new_serial = wx.TextCtrl(dlg, -1, old_serial)
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(wx.Button(dlg, wx.ID_OK), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(wx.Button(dlg, wx.ID_CANCEL), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(new_serial, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.CenterOnScreen()
        serial = ""
        if dlg.ShowModal() == wx.ID_OK:
            serial = new_serial.GetValue()
        dlg.Destroy()
        return serial

    def set_auto_scale(self, en):
        """this enables/disables the use of the 'Axes Limits' controls based on
        wether or not the 'Auto Scale' feature is active."""
        self.y_axis_max.Enable(en)
        self.y_axis_min.Enable(en)
        self.x_axis_max.Enable(en)
        self.x_axis_min.Enable(en)

    def enable_toolbar_controls(self, event):
        """this method disables the snap_shot button whenever we are in
        continuous measurement mode and renables upon exit. the purpose so we
        don't communication jams trying to tell the spec to take/give measurements
        at the same time"""
        self.snap_shot.Enable(event.enable)

    def show_help_menu(self, menu_tab):
        """displays a help menu. we need to check if one has been created already
        in case the user try's to open a new help menu. the menu_tab parameter
        sepcifies which tab to open to initially"""
        if not hasattr(self, 'help_frame'):
            self.help_frame = wx.Frame(None, title="Apogee Spectrovision Help",
                                       size=(500, 400))
            if IS_MAC:
                icon = wx.Icon('image_source/apogee-icon-256.png',
                               wx.BITMAP_TYPE_PNG)
                tb_icon = wx.TaskBarIcon(iconType=wx.TBI_DOCK)
                tb_icon.SetIcon(icon, "Apogee Spectrovision")
            elif IS_WIN:
                icon = wx.Icon("image_source\\apogee-icon-256.png")
            elif IS_GTK:
                icon = wx.Icon('image_source/apogee-icon-256.png', wx.BITMAP_TYPE_PNG)
            self.help_frame.SetIcon(icon)
            p = wx.Panel(self.help_frame)
            self.nb = nb = wx.Notebook(p)
            nb.AddPage(HelpPanel(nb, LEFTPANEL_HELP), "Left Panel/Status Bar")
            nb.AddPage(HelpPanel(nb, MENUBAR_HELP), "MenuBar")
            nb.AddPage(HelpPanel(nb, TOOLBAR_HELP), "ToolBar")
            nb.AddPage(HelpPanel(nb, PLOTVIEW_HELP), "PlotView")
            nb.AddPage(HelpPanel(nb, ABOUT_TEXT), "About Apogee Spectrovision")
            sizer = wx.BoxSizer()
            sizer.Add(nb, 1, wx.EXPAND)
            p.SetSizer(sizer)
        try:
            self.nb.ChangeSelection(menu_tab)
            self.help_frame.Show()
        except Exception:
            self.help_frame = None
            del(self.help_frame)
            self.show_help_menu(menu_tab)

    def get_red_farred(self, current):
        dlg = wx.Dialog(self.frame, -1, "Update Red and Far Red Range")
        dlg.SetBackgroundColour("white")
        red_label = wx.StaticText(dlg, -1, "Red Range")
        r_max_text = wx.StaticText(dlg, -1, "Max")
        r_min_text = wx.StaticText(dlg, -1, "Min")
        r_axis_min = wx.SpinCtrl(dlg,  min=340, max=1100,
                                 size=(70, -1))
        r_axis_min.SetValue(current[0][0])
        r_axis_max = wx.SpinCtrl(dlg,  min=340, max=1100,
                                 size=(70, -1))
        r_axis_max.SetValue(current[0][1])
        farred_label = wx.StaticText(dlg, -1, "Far Red Range")
        fr_max_text = wx.StaticText(dlg, -1, "Max")
        fr_min_text = wx.StaticText(dlg, -1, "Min")
        fr_axis_min = wx.SpinCtrl(dlg,  min=340, max=1100,
                                 size=(70, -1))
        fr_axis_min.SetValue(current[1][0])
        fr_axis_max = wx.SpinCtrl(dlg,  min=340, max=1100,
                                 size=(70, -1))
        fr_axis_max.SetValue(current[1][1])


        divider = wx.StaticLine(dlg, -1)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(divider, 0, wx.EXPAND | wx.ALL, border=5)
        sizer.Add(red_label, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(r_min_text, 1, wx.ALIGN_CENTER | wx.ALL)
        v_sizer.Add(r_axis_min, 1, wx.ALIGN_CENTER | wx.ALL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        horizontal_sizer.Add(v_sizer, 0, wx.ALIGN_CENTER | wx.ALL)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(r_max_text, 1, wx.ALIGN_CENTER | wx.ALL)
        v_sizer.Add(r_axis_max, 1, wx.ALIGN_CENTER | wx.ALL)
        horizontal_sizer.Add(v_sizer, 0, wx.ALIGN_CENTER | wx.ALL)

        sizer.Add(horizontal_sizer, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        sizer.AddSpacer(10)

        sizer.Add(farred_label, 0, wx.ALIGN_CENTER | wx.ALIGN_TOP | wx.ALL)
        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(fr_min_text, 1, wx.ALIGN_CENTER | wx.ALL)
        v_sizer.Add(fr_axis_min, 1, wx.ALIGN_CENTER | wx.ALL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        horizontal_sizer.Add(v_sizer, 0, wx.ALIGN_CENTER | wx.ALL)

        v_sizer = wx.BoxSizer(wx.VERTICAL)
        v_sizer.Add(fr_max_text, 1, wx.ALIGN_CENTER | wx.ALL)
        v_sizer.Add(fr_axis_max, 1, wx.ALIGN_CENTER | wx.ALL)
        horizontal_sizer.Add(v_sizer, 0, wx.ALIGN_CENTER | wx.ALL)

        sizer.Add(horizontal_sizer, 0, wx.ALIGN_CENTER | wx.ALL)

        divider = wx.StaticLine(dlg, -1)
        sizer.Add(divider, 0, wx.EXPAND | wx.ALL, border=5)

        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(wx.Button(dlg, wx.ID_OK), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(wx.Button(dlg, wx.ID_CANCEL), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, border=5)

        dlg.SetSizer(sizer)
        dlg.Fit()
        if dlg.ShowModal() == wx.ID_OK:
            return ([r_axis_min.GetValue(), r_axis_max.GetValue()],
                    [fr_axis_min.GetValue(), fr_axis_max.GetValue()])
        return None

    def get_sensor_pair(self, selected, choices):
        dlg = wx.Dialog(self.frame, -1, "Choose Sensor Pair")
        dlg.SetBackgroundColour("white")
        dlg.CenterOnParent()
        text = wx.StaticText(dlg, -1, "Choose a sensor to pair with %s" % selected)
        cb = wx.ComboBox(dlg, -1, choices=choices)
        sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.Add(wx.Button(dlg, wx.ID_OK), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        button_sizer.Add(wx.Button(dlg, wx.ID_CANCEL), 0,
                         wx.ALIGN_CENTER | wx.ALL, 5)
        sizer.Add(text, 0, wx.ALIGN_CENTER | wx.ALL, border=5)
        sizer.Add(cb, 0, wx.ALIGN_CENTER | wx.ALL, border=5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, border=5)
        dlg.SetSizer(sizer)
        dlg.Fit()
        if dlg.ShowModal() == wx.ID_OK:
            return cb.GetValue()
        return ""

    def set_pair(self, pair):
        if not IS_WIN:
            image_path = 'image_source/paired_sensor.jpg'
        else:
            image_path = 'image_source\\paired_sensor.jpg'
        for sensor in self.sensors:
            if sensor.GetLabel() in pair:
                sensor.SetBitmapLabel(wx.Bitmap(image_path))
        self.tool_bar.Refresh()

    def remove_pair(self, pair):
        if not IS_WIN:
            image_path = 'image_source/sensor.jpg'
        else:
            image_path = 'image_source\\sensor.jpg'
        for sensor in self.sensors:
            if sensor.GetLabel() in pair:
                sensor.SetBitmapLabel(wx.Bitmap(image_path))
                sensor.Refresh()
        self.tool_bar.Refresh()

    def number_pad(self, event):
        from constants import SERVICED
        #event.Skip()
        if SERVICED:
            SERVICED = False
            return
        widget = event.GetEventObject()
        #if widget.Name == 'text':
            #widget.Bind(wx.EVT_CHILD_FOCUS, None)
        #else:
            #widget.Unbind(wx.EVT_SET_FOCUS)
        dlg = wx.Dialog(self.frame, -1, 'Number Entry')
        dlg.SetBackgroundColour("white")
        number = wx.TextCtrl(dlg, -1, str(widget.GetValue()), size=(120, -1))
        number.SetSelection(-1, -1)
        one = wx.Button(dlg, -1, "1", size=(38,38))
        two = wx.Button(dlg, -1, "2", size=(38,38))
        three = wx.Button(dlg, -1, "3", size=(38,38))
        four = wx.Button(dlg, -1, "4", size=(38,38))
        five = wx.Button(dlg, -1, "5", size=(38,38))
        six = wx.Button(dlg, -1, "6", size=(38,38))
        seven = wx.Button(dlg, -1, "7", size=(38,38))
        eight = wx.Button(dlg, -1, "8", size=(38,38))
        nine = wx.Button(dlg, -1, "9", size=(38,38))
        zero = wx.Button(dlg, -1, "0", size=(38,38))
        backspace = wx.Button(dlg, -1, "<---", size=(38, 38))
        decimal = wx.Button(dlg, -1, ".", size=(38, 38))
        def update_number(event):
            selection = number.GetSelection()
            label = event.GetEventObject().GetLabel()
            selection = number.GetValue()[selection[0]:selection[1]]
            if label == "<---":
                if selection:
                    number.SetValue(number.GetValue().replace(selection, ''))
                else:
                    number.SetValue(number.GetValue()[:-1])
            else:
                if selection:
                    number.SetValue(number.GetValue().replace(selection, label))
                else:
                    number.SetValue(number.GetValue() + label)
        one.Bind(wx.EVT_BUTTON, update_number)
        two.Bind(wx.EVT_BUTTON, update_number)
        three.Bind(wx.EVT_BUTTON, update_number)
        four.Bind(wx.EVT_BUTTON, update_number)
        five.Bind(wx.EVT_BUTTON, update_number)
        six.Bind(wx.EVT_BUTTON, update_number)
        seven.Bind(wx.EVT_BUTTON, update_number)
        eight.Bind(wx.EVT_BUTTON, update_number)
        nine.Bind(wx.EVT_BUTTON, update_number)
        zero.Bind(wx.EVT_BUTTON, update_number)
        backspace.Bind(wx.EVT_BUTTON, update_number)
        decimal.Bind(wx.EVT_BUTTON, update_number)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(number, 0, wx.CENTER | wx.ALL, 5)
        grid_sizer = wx.GridSizer(4, 3, 2, 2)
        grid_sizer.Add(one)
        grid_sizer.Add(two)
        grid_sizer.Add(three)
        grid_sizer.Add(four)
        grid_sizer.Add(five)
        grid_sizer.Add(six)
        grid_sizer.Add(seven)
        grid_sizer.Add(eight)
        grid_sizer.Add(nine)
        grid_sizer.Add(backspace)
        grid_sizer.Add(zero)
        grid_sizer.Add(decimal)
        sizer.Add(grid_sizer, flag=wx.CENTER | wx.ALL)
        ok = wx.Button(dlg, wx.ID_OK, size=(55, -1))
        cncl = wx.Button(dlg, wx.ID_CANCEL, size=(55, -1))
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(ok, border=3)
        h_sizer.Add(cncl, border=3)
        sizer.Add(h_sizer, flag=wx.CENTER | wx.ALL, border=7)
        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.CenterOnParent()
        self.stop_button.SetFocus()
        if dlg.ShowModal() == wx.ID_OK:
            try:
                widget.SetValue(number.GetValue())
            except TypeError:
                try:
                    widget.SetValue(int(float(number.GetValue())))
                except Exception:
                    pass
        SERVICED = True
        #widget.Bind(wx.EVT_CHILD_FOCUS, self.number_pad)
        #widget.Bind(wx.EVT_SET_FOCUS, self.number_pad)
        #event.Skip()

class HelpPanel(wx.Panel):
    def __init__(self, parent, text):
        """standard help menu panel class. all pages in the help menu notebook
        are derived from this class."""
        super(HelpPanel, self).__init__(parent)
        sizer = wx.BoxSizer()
        t = wx.TextCtrl(self, -1, text,
                        style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(t, 1, wx.EXPAND)
        self.SetSizer(sizer)

# The classes below are unused for now unless someone decides they want fancy
# text in the help menu. Currently the help menu is in super rough draft mode

class LeftPanelHelp(wx.Panel):
    def __init__(self, parent):
        super(LeftPanelHelp, self).__init__(parent)
        sizer = wx.BoxSizer()
        t = wx.TextCtrl(self, -1, LEFTPANEL_HELP,
                        style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(t, 1, wx.EXPAND)
        self.SetSizer(sizer)


class MenuBarHelp(wx.Panel):
    def __init__(self, parent):
        super(MenuBarHelp, self).__init__(parent)
        sizer = wx.BoxSizer()
        t = wx.TextCtrl(self, -1, MENUBAR_HELP,
                        style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(t, 1, wx.EXPAND)
        self.SetSizer(sizer)


class ToolbarHelp(wx.Panel):
    def __init__(self, parent):
        super(ToolbarHelp, self).__init__(parent)
        sizer = wx.BoxSizer()
        t = wx.TextCtrl(self, -1, TOOLBAR_HELP,
                        style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(t, 1, wx.EXPAND)
        self.SetSizer(sizer)


class PlotViewHelp(wx.Panel):
    def __init__(self, parent):
        super(PlotViewHelp, self).__init__(parent)
        sizer - wx.BoxSizer()
        t = wx.TextCtrl(self, -1, TOOLBAR_HELP,
                        style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(t, 1, wx.EXPAND)
        self.SetSizer(sizer)



class AboutAS(wx.Panel):
    def __init__(self, parent):
        super(AboutAS, self).__init__(parent)
        sizer = wx.BoxSizer()
        t = wx.TextCtrl(self, -1, "About Apogee Spectrovision will go here.",
                        style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(t, 1, wx.EXPAND)
        self.SetSizer(sizer)

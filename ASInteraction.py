# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import wx

from constants import RELATIVE, RT, PHOTON_FLUX, ILLUMINANCE, ENERGY_FLUX,\
     LUX, FOOTCANDLE


class ASInteraction(object):
    def install(self, control, presentation):
        self.control = control

        # bind menu bar
        # file menu
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_data_capture,
                                id=100)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_connect,
                                id=101)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_disconnect,
                                id=102)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_red_farred,
                                id=103)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_exit, id=wx.ID_EXIT)

        # view menu
        presentation.frame.Bind(wx.EVT_MENU, lambda event:
                                self.on_view_menu(event, raw=True), id=200)
        presentation.frame.Bind(wx.EVT_MENU, lambda event:
                                self.on_view_menu(event, r_t=True), id=201)
        presentation.frame.Bind(wx.EVT_MENU, lambda event: 
                                self.on_view_menu(event, pf=True), id=202)
        presentation.frame.Bind(wx.EVT_MENU, lambda event:
                                self.on_view_menu(event, ef=True), id=203)
        presentation.frame.Bind(wx.EVT_MENU, lambda event:
                                self.on_view_menu(event, lx=True), id=204)
        presentation.frame.Bind(wx.EVT_MENU, lambda event:
                                self.on_view_menu(event, fc=True), id=205)

        # help menu
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_leftpanel_help, id=300)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_menubar_help, id=301)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_toolbar_help, id=302)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_plot_help, id=303)
        presentation.frame.Bind(wx.EVT_MENU, self.on_menu_about, id=304)

        # bind top frame controls
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_dark_reference,
                                presentation.dark_reference)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_light_reference,
                                presentation.light_reference)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_clear_dark_scan,
                                presentation.clear_dark_ref)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_open_file,
                                presentation.open_file)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_save_spectrum,
                                presentation.save_spectrum)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_save_data,
                                presentation.save_data)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_save_data_and_spectrum,
                                presentation.save_both)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_copy_graph_image,
                                presentation.copy_graph_image)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_plot_first_deriv,
                                presentation.first_derivative)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_plot_second_deriv,
                                presentation.second_derivative)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_pause_thread,
                                presentation.pause_button)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_start_thread,
                                presentation.play_button)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_stop_thread,
                                presentation.stop_button)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_snap_shot,
                                presentation.snap_shot)

        # bind left frame controls
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_integ_time_change,
                                presentation.integration_time)
        presentation.frame.Bind(wx.EVT_SPINCTRL, self.on_integ_time_change,
                                presentation.integration_time)
        presentation.frame.Bind(wx.EVT_TOGGLEBUTTON,
                                self.on_set_auto_integration,
                                presentation.auto_integration)
        presentation.frame.Bind(wx.EVT_SPINCTRL, self.on_avg_scan_change,
                                presentation.number_of_scans_to_avg)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.relative)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.r_t)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.photon_flux)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.energy_flux)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.illuminance)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.lux)
        presentation.frame.Bind(wx.EVT_RADIOBUTTON, self.on_graph_mode_change,
                                presentation.footcandle)
        presentation.frame.Bind(wx.EVT_SPINCTRL, self.on_integ_range_change,
                                presentation.integ_max)
        presentation.frame.Bind(wx.EVT_SPINCTRL, self.on_integ_range_change,
                                presentation.integ_min)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_integ_range_change,
                                presentation.integ_max)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_integ_range_change,
                                presentation.fraction_min)
        presentation.frame.Bind(wx.EVT_SPINCTRL, self.on_integ_range_change,
                                presentation.fraction_max)
        presentation.frame.Bind(wx.EVT_SPINCTRL, self.on_integ_range_change,
                                presentation.fraction_min)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_integ_range_change,
                                presentation.fraction_max)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_integ_range_change,
                                presentation.integ_min)
        presentation.frame.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_axis_change,
                                presentation.y_axis_max)
        presentation.frame.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_y_axis_change,
                                presentation.y_axis_min)
        presentation.frame.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_axis_change,
                                presentation.x_axis_max)
        presentation.frame.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_x_axis_change,
                                presentation.x_axis_min)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_axis_enter,
                                presentation.y_axis_max)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_axis_enter,
                                presentation.y_axis_min)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_axis_enter,
                                presentation.x_axis_max)
        presentation.frame.Bind(wx.EVT_TEXT_ENTER, self.on_axis_enter,
                                presentation.x_axis_min)
        presentation.frame.Bind(wx.EVT_TOGGLEBUTTON, self.on_set_auto_scale,
                                presentation.auto_scale_toggle)
        presentation.frame.Bind(wx.EVT_BUTTON, self.on_refresh_plot,
                                presentation.reset_button)
        presentation.frame.Bind(wx.EVT_TOGGLEBUTTON, self.on_show_average,
                                presentation.show_average_button)

        self.axis_controls = [presentation.y_axis_min, presentation.y_axis_max,
                              presentation.x_axis_min, presentation.x_axis_max]

        # key binding for calibration mode
        ID_CALIBRATE = wx.NewId()
        ID_SNAPSHOT = wx.NewId()
        ID_PAUSE = wx.NewId()
        ID_STOP = wx.NewId()
        ID_PLAY = wx.NewId()
        SAVE_BOTH = wx.NewId()
        table_data = [(wx.ACCEL_CTRL | wx.ACCEL_SHIFT, wx.WXK_F10, ID_CALIBRATE),
                      (wx.ACCEL_NORMAL, wx.WXK_F1, ID_SNAPSHOT),
                      (wx.ACCEL_NORMAL, wx.WXK_F2, ID_PLAY),
                      (wx.ACCEL_NORMAL, wx.WXK_F3, ID_PAUSE),
                      (wx.ACCEL_NORMAL, wx.WXK_F4, ID_STOP),
                      (wx.ACCEL_CTRL, ord('d'), wx.ID_SAVE),
                      (wx.ACCEL_CTRL, ord('s'), wx.ID_SAVEAS),
                      (wx.ACCEL_CTRL, ord('c'), wx.ID_COPY),
                      (wx.ACCEL_CTRL, ord('o'), wx.ID_OPEN),
                      (wx.ACCEL_CTRL, ord('a'), SAVE_BOTH)]
        presentation.frame.SetAcceleratorTable(wx.AcceleratorTable(table_data))
        presentation.frame.Bind(wx.EVT_MENU, self.on_swtich_to_calibrate_mode,
                                id=ID_CALIBRATE)
        presentation.frame.Bind(wx.EVT_MENU, self.on_snap_shot, id=ID_SNAPSHOT)
        presentation.frame.Bind(wx.EVT_MENU, self.on_start_thread, id=ID_PLAY)
        presentation.frame.Bind(wx.EVT_MENU, self.on_pause_thread, id=ID_PAUSE)
        presentation.frame.Bind(wx.EVT_MENU, self.on_stop_thread, id=ID_STOP)
        presentation.frame.Bind(wx.EVT_MENU, self.on_save_data, id=wx.ID_SAVE)
        presentation.frame.Bind(wx.EVT_MENU, self.on_save_spectrum,
                                id=wx.ID_SAVEAS)
        presentation.frame.Bind(wx.EVT_MENU, self.on_save_data_and_spectrum,
                                id=SAVE_BOTH)
        presentation.frame.Bind(wx.EVT_MENU, self.on_copy_graph_image,
                                id=wx.ID_COPY)
        presentation.frame.Bind(wx.EVT_MENU, self.on_open_file, id=wx.ID_OPEN)
        # capture close so we can shutdown non daemon threads on exit
        presentation.frame.Bind(wx.EVT_CLOSE, self.on_close)
    # these methods catch the interrupts sent from the presentations controls
    # and direct them to methods in ASControl.py

    def on_menu_data_capture(self, event):
        self.control.setup_data_capture()

    def on_menu_connect(self, event):
        self.control.connect_to_device()

    def on_menu_disconnect(self, event):
        self.control.disconnect_device()

    def on_menu_red_farred(self, event):
        self.control.update_red_farred()

    def on_menu_exit(self, event):
        self.control.shutdown_application()

    def on_close(self, event):
        self.control.stop_all_threads()
        event.Skip()

    def on_view_menu(self, event, raw=False, r_t=False, pf=False, ef=False,
                     lx=False, fc=False):
        if raw:
            mode = RELATIVE
        elif r_t:
            mode = RT
        elif pf:
            mode = PHOTON_FLUX
        elif ef:
            mode = ENERGY_FLUX
        else:
            mode = ILLUMINANCE
        units = None
        if lx:
            units = LUX
        elif fc:
            units = FOOTCANDLE
        self.control.change_plot_view(mode, units)

    def on_menu_leftpanel_help(self, event):
        self.control.show_help_menu(0)

    def on_menu_menubar_help(self, event):
        self.control.show_help_menu(1)

    def on_menu_toolbar_help(self, event):
        self.control.show_help_menu(2)

    def on_menu_plot_help(self, event):
        self.control.show_help_menu(3)

    def on_menu_about(self, event):
        self.control.show_help_menu(4)

    def on_dark_reference(self, event):
        self.control.set_dark_reference()

    def on_light_reference(self, event):
        self.control.set_light_reference()

    def on_clear_dark_scan(self, event):
        self.control.clear_dark_ref()

    def on_save_spectrum(self, event):
        self.control.save_spectrum()

    def on_open_file(self, event):
        self.control.plot_from_file()

    def on_save_data(self, event):
        self.control.save_data_to_file()

    def on_save_data_and_spectrum(self, event):
        self.control.save_data_to_file()
        self.control.save_spectrum()

    def on_copy_graph_image(self, event):
        self.control.copy_plot_to_clipboard()

    def on_plot_first_deriv(self, event):
        self.control.compute_and_plot_first_derivative()

    def on_plot_second_deriv(self, event):
        self.control.compute_and_plot_second_derivative()

    def on_pause_thread(self, event):
        self.control.pause_all_threads()

    def on_start_thread(self, event):
        self.control.start_plot_threads()

    def on_stop_thread(self, event):
        self.control.stop_all_threads()

    def on_snap_shot(self, event):
        self.control.take_and_plot_snapshot()

    def on_integ_time_change(self, event):
        self.control.update_integration_time()

    def on_integ_range_change(self, event):
        self.control.update_vlines()

    def on_set_auto_integration(self, event):
        self.control.set_auto_integration(event.GetEventObject().GetValue())

    def on_avg_scan_change(self, event):
        self.control.update_number_of_scans_to_average()

    def on_graph_mode_change(self, event):
        self.control.update_mode_and_units()

    def on_y_axis_change(self, event):
        self.control.validate_and_update_y_axis()

    def on_x_axis_change(self, event):
        self.control.validate_and_update_x_axis()

    # to get the events to process correctly, this method is used mainly to
    # deselect the current axes control so that a spinctrldouble event will
    # fire. incidentally, it also creates a nice user feature to select the
    # next axes control on enter.
    def on_axis_enter(self, event):
        obj = event.GetEventObject()
        index = self.axis_controls.index(obj) + 1
        if index == 4:
            index = 0
        self.axis_controls[index].SetFocus()

    def on_set_auto_scale(self, event):
        self.control.set_auto_scale(event.GetEventObject().GetValue())

    def on_refresh_plot(self, event):
        self.control.reset_original_plot()

    def on_show_average(self, event):
        self.control.toggle_average()

    def on_swtich_to_calibrate_mode(self, event):
        self.control.set_calibrate_mode()

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import wx
import wx.lib.masked as masked


def ok_cancel(window, title, msg):
    dlg = wx.MessageDialog(window, msg, title,
                           wx.OK | wx.CANCEL | wx.ICON_INFORMATION)
    dlg.CenterOnParent()
    response = dlg.ShowModal() == wx.ID_OK
    dlg.Destroy()
    return response


def give_error(window, title, msg):
    dlg = wx.MessageDialog(window, msg, title,
                           wx.OK | wx.STAY_ON_TOP | wx.ICON_HAND)
    dlg.ShowModal()
    dlg.Destroy()


def confirmation_message(msg, title):
    dlg = wx.MessageBox(msg, title, wx.OK | wx.ICON_INFORMATION)


def progress_dialog(title, msg, window, maximum):
    if maximum:
        dlg = wx.GenericProgressDialog(title, msg, maximum=maximum,
                                       parent=window,
                                       style=wx.PD_CAN_ABORT | wx.PD_APP_MODAL
                                       | wx.PD_AUTO_HIDE)
    else:
        dlg = wx.GenericProgressDialog(title, msg, parent=window,
                                       style=wx.PD_CAN_ABORT | wx.PD_APP_MODAL
                                       | wx.PD_AUTO_HIDE)
    dlg.CenterOnScreen()
    return dlg

def time_control(window, title, text):
    dlg = wx.Dialog(window, -1, title)
    text = wx.StaticText(dlg, -1, text)
    spin = wx.SpinButton(dlg, -1, wx.DefaultPosition, (-1,30), wx.SP_VERTICAL)
    time24 = masked.TimeCtrl(dlg, -1, fmt24hr=True, spinButton=spin)
    ok = wx.Button(dlg, wx.ID_OK)
    cancel = wx.Button(dlg, wx.ID_CANCEL)
    btn_sizer = wx.StdDialogButtonSizer()
    h_sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(text, 0, wx.ALIGN_CENTER | wx.ALL, 5)
    h_sizer.Add(time24, 0, wx.ALIGN_CENTER | wx.ALL, 0)
    h_sizer.Add(spin, 0, wx.ALIGN_CENTER | wx.ALL, 0)
    sizer.Add(h_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
    btn_sizer.Add(ok, 0, wx.ALIGN_CENTER | wx.ALL, 5)
    btn_sizer.Add(cancel, 0, wx.ALIGN_CENTER | wx.ALL, 5)
    sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)
    dlg.SetSizer(sizer)
    dlg.Fit()
    dlg.CenterOnScreen()
    start_time = None
    if dlg.ShowModal() == wx.ID_OK:
        start_time = time24.GetValue()
    dlg.Destroy()
    return start_time

def open_file_dialog(window, title, wildcard="", current_dir="", current_file=""):
    dlg = wx.FileDialog(window, title, current_dir, current_file, wildcard,
                        style=wx.FD_OPEN)
    while dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    dlg.Destroy()

def save_file_dialog(window, title, wildcard="", current_dir="", current_file=""
                     , overwrite_prompt=True):
    if overwrite_prompt:
        dlg = wx.FileDialog(window, title, current_dir, current_file, wildcard,
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
    else:
        dlg = wx.FileDialog(window, title, current_dir, current_file, wildcard,
                            style=wx.FD_SAVE)
    while dlg.ShowModal() == wx.ID_OK:
        path = dlg.GetPath()
        dlg.Destroy()
        return path
    dlg.Destroy()

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
import logging
import os
import sys
import tempfile
import wx
LOG_FILE_NAME = os.path.join(tempfile.gettempdir(), 'ApogeeSpectrovisionLog.txt')
logging.basicConfig(filename=LOG_FILE_NAME, level=logging.DEBUG)
# redirect error messages to this logfile in append mode so we don't lose error
# logs from previous iterations
sys.stderr = open(LOG_FILE_NAME, 'a')

try:
    if getattr(sys, 'frozen', False):
        sys.path.append(sys._MEIPASS)
    else:
        sys.path.append(os.path.realpath("../.."))
except Exception:
    sys.path.append(os.path.realpath("../.."))
if 'wxMSW' in wx.PlatformInfo:
    import ctypes
    myappid = 'ApogeeSpectrovision'
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

from wx import App

from ASAbstraction import ASAbstraction
from ASControl import ASControl
from ASInteraction import ASInteraction
from ASPresentation import ASPresentation


class ApogeeSpectrovision(App):
    def OnInit(self):
        abstraction = ASAbstraction()
        presentation = ASPresentation(abstraction.red_farred)
        interaction = ASInteraction()
        ASControl(abstraction, interaction, presentation)
        return True


if __name__ == '__main__':
    errors = False
    try:
        # create application
        application = ApogeeSpectrovision(redirect=False)
    except:
        # this catches any errors that occured during the init methods and writes
        # to the error log file including full traceback info
        logging.exception('An error occured: %s' % datetime.datetime.now())
        errors = True
    else:
        # read initial file size
        filesize = 0
        log_file = open(LOG_FILE_NAME, 'r')
        filesize = len(log_file.read())

        # run application
        application.MainLoop()
        # flush stderr so that file gets written before we try to read the size
        sys.stderr.flush()
        # get size of file after application has exited
        endfilesize = 0
        log_file = open(LOG_FILE_NAME, 'r')
        endfilesize = len(log_file.read())
        if endfilesize > filesize:
            errors = True
    if errors:
        # if any errors occured, inform the user and ask if they would like to
        # view the log file. could potentially set this up to automatically
        # email the bug reports list in trello if we wanted to. more research
        # needed to determine efficacy
        dlg = wx.MessageDialog(
            None,
            "An error has occured. Would you like to view the log file at:\n%s" % LOG_FILE_NAME,
            "Apogee Spectrovision Error!", wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            if 'wxMSW' in wx.PlatformInfo:
                os.startfile(LOG_FILE_NAME)
            else:
                import subprocess
                subprocess.call(["open", LOG_FILE_NAME])

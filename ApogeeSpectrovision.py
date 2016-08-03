# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import wx
import sys
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
        presentation = ASPresentation()
        interaction = ASInteraction()
        ASControl(abstraction, interaction, presentation)
        return True


if __name__ == '__main__':
    application = ApogeeSpectrovision(redirect=False)
    application.MainLoop()

# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 10:24:49 2014

@author: chuong nguyen, chuong.nguyen@anu.edu.au
"""

import sys
import cv2
import urllib
import numpy as np
import time
import re


class Camera(object):
    """
    Control ACTi Camera
    Ref: http://www2.acti.com/getfile/KnowledgeBase_UploadFile/ACTi_Camera_URL_Commands_20120327_002.pdf
    """
    def __init__(self, IP, User, Password, ImageSize=None):
        self.IP = IP
        self.HTTPLogin = "http://{}/cgi-bin/encoder?"\
            "USER={}&PWD={}".format(IP, User, Password)
        self.IMAGE_SIZES = [[1920, 1080], [1280, 720], [640, 480]]
        if ImageSize:
            assert(ImageSize in self.IMAGE_SIZES)
            self.ImageSize = ImageSize
        self.Image = None
        self.PhotoIndex = 0

        self.Commands = {}
        self.Commands["zoom_range"] = "&ZOOM_CAP_GET"
        self.Commands["zoom_curpos"] = "&ZOOM_POSITION"
        self.Commands["zoom_mode"] = "&ZOOM={}"
        self.Commands["zoom_set"] = "&ZOOM={},{}"
        self.Commands["zoom_step"] = "&STEPPED_ZOOM={},{}"

        self.Commands["focus_range"] = "&FOCUS_CAP_GET"
        self.Commands["focus_curpos"] = "&FOCUS_POSITION"
        self.Commands["focus_mode"] = "&FOCUS={}"
        self.Commands["focus_set"] = "&FOCUS={},{}"
        self.Commands["focus_step"] = "&STEPPED_FOCUS={},{}"

        self.Commands["snap_photo"] = "&SNAPSHOT=N{}x{},100&DUMMY={}"

        # Valid values for ACTi camera
        self.ZOOM_MODES = ["STOPS"]
        self.ZOOM_STATES = ["DIRECT", "TELE"]
        self.ZOOM_STEP_DIRECTIONS = ["TELE", "WIDE"]
        self.ZOOM_STEP_RANGE = [1, 255]
        self.ZOOM_DIRECT_RANGE = self.getZoomRange()

        self.FOCUS_MODES = ["STOP", "FAR", "NEAR", "AUTO", "MANUAL", "ZOOM_AF",
                            "REFOCUS"]
        self.FOCUS_STATES = ["DIRECT"]
        self.FOCUS_STEP_DIRECTIONS = ["NEAR", "FAR"]
        self.FOCUS_STEP_RANGE = [1, 255]
        self.FOCUS_DIRECT_RANGE = self.getFocusRange()

        print(self.status())

    def snapPhoto(self, ImageSize=None):
        if ImageSize and ImageSize in self.IMAGE_SIZES:
            stream = urllib.urlopen(self.HTTPLogin +
                                    self.Commands["snap_photo"].format(
                                        ImageSize[0], ImageSize[1],
                                        self.PhotoIndex))
        else:
            stream = urllib.urlopen(self.HTTPLogin +
                                    self.Commands["snap_photo"].format(
                                        self.ImageSize[0], self.ImageSize[1],
                                        self.PhotoIndex))
        jpg_bytearray = np.asarray(bytearray(stream.read()), dtype=np.uint8)
        self.Image = cv2.imdecode(jpg_bytearray, cv2.CV_LOAD_IMAGE_COLOR)
        self.PhotoIndex += 1
        return self.Image

    def getValue(self, Text):
        Text = Text.split("=")
        TextValue = re.sub("'", "", Text[1])
        ValueList = TextValue.split(",")
#        ValueList = [float(Value) if Value.isdigit() else Value
#                     for Value in ValueList]
        return ValueList

    def zoomStep(self, Direction, StepSize):
        if Direction.lower() == "in":
            Direction = "TELE"
        elif Direction.lower() == "out":
            Direction = "WIDE"
        assert(Direction in self.ZOOM_STEP_DIRECTIONS and
               StepSize >= self.ZOOM_STEP_RANGE[0] and
               StepSize <= self.ZOOM_STEP_RANGE[1])
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["zoom_step"].format(
                                    Direction, StepSize))
        Output = stream.read(1024).strip()
        return Output

    def setZoomPosition(self, AbsPosition):
        assert(AbsPosition >= self.ZOOM_DIRECT_RANGE[0] and
               AbsPosition <= self.ZOOM_DIRECT_RANGE[1])
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["zoom_set"].format(
                                    "Direct", AbsPosition))
        Output = stream.read(1024).strip()
        return Output

    def getZoomPosition(self):
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["zoom_curpos"])
        Output = stream.read(1024).strip()
        Position = self.getValue(Output)
        return Position[0]

    def getZoomRange(self):
        stream = urllib.urlopen(self.HTTPLogin + self.Commands["zoom_range"])
        Outptput = stream.read(1024).strip()
        return self.getValue(Outptput)

    def getFocusPosition(self):
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["focus_curpos"])
        Output = stream.read(1024).strip()
        Position = self.getValue(Output)
        return Position[0]

    def getFocusRange(self):
        stream = urllib.urlopen(self.HTTPLogin + self.Commands["focus_range"])
        Outptput = stream.read(1024).strip()
        Values = self.getValue(Outptput)
        # ex: Values = ["Motorized", 1029.0, 221.0]
        Range = Values[2:0:-1]
        return Range

    def updateStatus(self):
        self.zoomPos = self.getZoomPosition()
        self.zoomRange = self.getZoomRange()
        self.focusPos = self.getFocusPosition()
        self.focusRange = self.getFocusRange()

    def status(self):
        self.updateStatus()
        return("ZoomPos = {}. FocusPos = {}.".format(self.zoomPos,
                                                     self.focusPos))


class PanTiltUnit(object):
    """
    Control J-Systems PTZ
    """
    def __init__(self, IP, User=None, Password=None):
        self.IP = IP
        self.User = User
        self.Password = Password
        self.Link = "http://{}".format(self.IP)
        print(self.status())

    def getKeyValue(self, MessageXML, Key):
        KeyStart = "<{}>".format(Key)
        KeyEnd = "</{}>".format(Key)
        Start = MessageXML.find(KeyStart)
        # Sometimes KeyStart is missing
        if Start < 0:
            Start = 0
        else:
            Start = Start + len(KeyStart)
        End = MessageXML.find(KeyEnd, Start)
        if End > Start:
            Value = MessageXML[Start:End].strip()
#            if Value.isdigit():
#                return float(Value)
            return Value
        else:
            return ""

    def panStep(self, Direction, Steps):
        assert(abs(Steps) <= 127)
        Dir = 1
        if Direction.lower() == "left":
            Dir = -1
        Url = self.Link + "/Bump.xml?PCmd={}".format(Dir*Steps)
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        Info = self.getKeyValue(Output, "Text")
        return Info

    def tiltStep(self, Direction, Steps):
        assert(abs(Steps) <= 127)
        Dir = 1
        if Direction.lower() == "down":
            Dir = -1
        Url = self.Link + "/Bump.xml?TCmd={}".format(Dir*Steps)
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        Info = self.getKeyValue(Output, "Text")
        return Info

    def setPanTiltPosition(self, PanDegree=0, TiltDegree=0):
        Url = self.Link + "/Bump.xml?GoToP={}&GoToT={}".format(
            int(PanDegree*10), int(TiltDegree*10))
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        print(Output)
        Info = self.getKeyValue(Output, "Text")
        return Info

    def setPanPosition(self, Degree):
        Info = self.setPanTiltPosition(PanDegree=Degree)
#        Url = self.Link + "/CP_Update.xml"
#        stream = urllib.urlopen(Url)
#        Output = stream.read(1024)
#        self.PanPos = self.getKeyValue(Output, "PanPos")  # degrees
#        while self.PanPos != "{f}"Degree
        return Info

    def setTiltPosition(self, Degree):
        Info = self.setPanTiltPosition(TiltDegree=Degree)
        return Info

    def getPanPosition(self):
        self.updateStatus()
        return self.PanPos

    def getTiltPosition(self):
        self.updateStatus()
        return self.TiltPos

    def getPanTiltPosition(self):
        self.updateStatus()
        return self.PanPos, self.TiltPos

    def updateStatus(self):
        Url = self.Link + "/CP_Update.xml"
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)

        self.PanPos = self.getKeyValue(Output, "PanPos")  # degrees
        self.TiltPos = self.getKeyValue(Output, "TiltPos")  # degrees

        # Limit switch states
        self.PCCWLS = self.getKeyValue(Output, "PCCWLS")
        self.PCWLS = self.getKeyValue(Output, "PCWLS")
        self.TDnLS = self.getKeyValue(Output, "TDnLS")
        self.TUpLS = self.getKeyValue(Output, "TUpLS")

        self.BattV = self.getKeyValue(Output, "BattV")  # Volt
        self.Heater = self.getKeyValue(Output, "Heater")
        self.Temp = self.getKeyValue(Output, "Temp")  # F degrees

        self.ListState = self.getKeyValue(Output, "ListState")
        self.ListIndex = self.getKeyValue(Output, "ListIndex")
        self.CtrlMode = self.getKeyValue(Output, "CtrlMode")

        self.AutoPatrol = self.getKeyValue(Output, "AutoPatrol")
        self.Dwell = self.getKeyValue(Output, "Dwell")  # seconds

    def status(self):
        self.updateStatus()
        return "PanPos = {} degrees. TiltPos = {} degrees.".format(
            self.PanPos, self.TiltPos)


def liveViewDemo(Camera, PanTil=None):
    while True:
        Image = Camera.snapPhoto()
        if Image is not None:
            cv2.imshow("Live view from {}".format(Camera.IP), Image)
        time.sleep(0.1)
        if sys.platform == 'win32':
            Key = cv2.waitKey(50)
        else:
            Key = 0xFF & cv2.waitKey(50)
        if Key != 27 and Key != 255 and Key != -1:
            print("Key = {}".format(Key))

        Info = ""
        if Key == 27:
            break
        elif Key == 81 or Key == 2424832:  # arrow left key
            Info = PanTil.panStep("left", 10)
            Info = PanTil.getPanPosition()
        elif Key == 83 or Key == 2555904:  # arrow right key
            Info = PanTil.panStep("right", 10)
            Info = PanTil.getPanPosition()
        elif Key == 82 or Key == 2490368:  # arrow up key
            Info = PanTil.tiltStep("up", 10)
            Info = PanTil.getTiltPosition()
        elif Key == 84 or Key == 2621440:  # arrow down key
            Info = PanTil.tiltStep("down", 10)
            Info = PanTil.getTiltPosition()
        elif Key == 85 or Key == 2162688:  # page up key
            Info = Camera.zoomStep("in", 50)
            Info = Camera.getZoomPosition()
        elif Key == 86 or Key == 2228224:  # page down key
            Info = Camera.zoomStep("out", 50)
            Info = Camera.getZoomPosition()
        elif Key == 115:  # s key
            Info = PanTil.status()
            Info += " " + Cam.status()

        if len(Info) > 0:
            print(Info)

if __name__ == "__main__":
    Camera_IP = "192.168.1.100"
    Camera_User = "Admin"
    Camera_Password = "123456"
    Camera_ImageSize = [640, 480]  # [1920, 1080]
    Cam = Camera(Camera_IP, Camera_User, Camera_Password, Camera_ImageSize)

    PanTil_IP = "192.168.1.101"
    PanTil = PanTiltUnit(PanTil_IP)

    liveViewDemo(Cam, PanTil)


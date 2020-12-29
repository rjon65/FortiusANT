#-------------------------------------------------------------------------------
# Version info
#-------------------------------------------------------------------------------
__version__ = "2020-12-17"
# 2020-12-17    First version based on ExplorAnt
#-------------------------------------------------------------------------------
import argparse
import binascii
import math
import numpy
import os
import pickle
import platform, glob
import random
import sys
import struct
import threading
import time
import usb.core
import wx
import random

from datetime import datetime

import structConstants      as sc
import antDongle            as ant
import debug
import BushidoBridgeCommand as cmd
import logfile

# ------------------------------------------------------------------------------

debug.deactivate()
clv = cmd.CommandLineVariables()
debug.activate(clv.debug)

# ------------------------------------------------------------------------------
# CSV file for analysis
# Writing out data pages
# ------------------------------------------------------------------------------

filename = "BushidoBridge." + datetime.now().strftime('%Y-%m-%d %H-%M-%S') + ".csv"

if clv.csvExport:
    csvFile = open(filename, "w+")

firstWrite = True

def WriteCsv(info, TX = False):
    global firstWrite
    global startLogging
    if firstWrite:
        firstWrite = False
        startLogging = datetime.now()
        logText = "Timestamp; Channel; Page; Payload 1; Payload 2; Payload 3; Payload 4;Payload 5; Payload 6; Payload 7; Mode \n"
    else:
        logText = ""

    nChannel = 0
    fChannel = sc.unsigned_char  # 0 First byte of the ANT+ message content
    nDataPageNumber = 1
    fDataPageNumber = sc.unsigned_char  # payload[0]        First byte of the ANT+ datapage
    nData1 = 2
    fData1 = sc.unsigned_char  # payload[1]
    nData2 = 3
    fData2 = sc.unsigned_char  # payload[2]
    nData3 = 4
    fData3 = sc.unsigned_char  # payload[3]
    nData4 = 5
    fData4 = sc.unsigned_char  # payload[4]
    nData5 = 6
    fData5 = sc.unsigned_char  # payload[5]
    nData6 = 7
    fData6 = sc.unsigned_char  # payload[6]
    nData7 = 8
    fData7 = sc.unsigned_char  # payload[7]

    format = sc.big_endian + fChannel + fDataPageNumber + fData1 + fData2 + fData3 + fData4 + fData5 + fData6 + fData7
    tuple = struct.unpack(format, info)

    now = datetime.now()
    delta = now - startLogging
    # millisecond resolution should be OK
    microDelta = int(delta.microseconds / 1000) + 1000*(delta.seconds)
    logText += str(microDelta) + "; "
    logText += str(int(tuple[nChannel])) + "; "
    logText += str(int(tuple[nDataPageNumber])) + "; "
    logText += str(int(tuple[nData1])) + "; "
    logText += str(int(tuple[nData2])) + "; "
    logText += str(int(tuple[nData3])) + "; "
    logText += str(int(tuple[nData4])) + "; "
    logText += str(int(tuple[nData5])) + "; "
    logText += str(int(tuple[nData6])) + "; "
    logText += str(int(tuple[nData7])) + "; "
    if TX:
        logText += "TX\n"
    else:
        logText += "RX\n"

    try:
        csvFile.write(logText)
        csvFile.flush()
    except:
        print("WriteCsv (" + logText + ") called, but file is not opened.")
        pass

# ------------------------------------------------------------------------------
# Generic data page routine
# ------------------------------------------------------------------------------

def genDataPageInfo (Channel, Page, PL1, PL2, PL3, PL4, PL5, PL6, PL7):

    fData            = sc.unsigned_char * 9

    format= sc.big_endian + fData
    info = struct.pack(format, Channel, Page, PL1, PL2, PL3, PL4, PL5, PL6, PL7)
    if debug.on(debug.Function):
        logfile.Write("Writing channel %2.2d Bushido page %2.2d: 0x%2.2x-%2.2x-%2.2x-%2.2x-%2.2x-%2.2x-%2.2x" % (Channel, Page, PL1, PL2, PL3, PL4, PL5, PL6, PL7))

    return info

# ------------------------------------------------------------------------------
# Log file with known data as a comma separated list
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Data to be written
# ------------------------------------------------------------------------------

# Common values BR/HU
BR_Power    = 0
BR_Speed    = 0
BR_Cadence  = 0
BR_Balance  = 0
BR_Temp     = 0
BR_Distance = 0
BR_Pback    = 0
BR_Alarm    = 0

HU_Power    = 0
HU_Speed    = 0
HU_Cadence  = 0
HU_Balance  = 0
HU_Temp     = 0
HU_Distance = 0
HU_Pback    = 0
HU_Alarm    = 0

# Specific values BR
BR_Vspeed   = 0
BR_ResL     = 0
BR_ResR     = 0
BR_Res1     = 0
BR_Res2     = 0

# Specific values HU
HU_Res      = 0
HU_Target   = 0


fileLog = "BushidoBridgeLog" + datetime.now().strftime('%Y-%m-%d %H-%M-%S') + ".csv"

if clv.csvExport:
    fileLog = open(fileLog, "w+")

firstLog = True

def WriteLog( TargetIsPower = True ):
    global firstLog
    global startLog
    if firstLog:
        firstLog = False
        startLog = datetime.now()
        if (TargetIsPower):
            logText = "Timestamp; HU_PowerTarget; "
        else:
            logText = "Timestamp; HU_SlopeTarget; "
                 
        logText += "BR_Power; HU_Power; BR_Speed; HU_Speed; BR_Vspeed; BR_Cadence;  HU_Cadence; BR_Balance; HU_Balance; " \
                     "BR_Temp; HU_Temp; BR_Distance; HU_Distance; BR_Pback; HU_Pback; BR_Alarm; HU_Alarm; " \
                     "HU_Res; BR_ResL; BR_ResR; BR_Res1; BR_Res2 \n"
    else:
        logText = ""

    now = datetime.now()
    delta = now - startLog
    # millisecond resolution should be OK
    msecDelta = int(delta.microseconds / 1000) + 1000*(delta.seconds)
    logText += str(msecDelta) + "; " + str(HU_Target) + "; " + str(BR_Power) + "; " + str(HU_Power) + "; " + str(BR_Speed) \
            + "; " + str(HU_Speed) + "; " + str(BR_Vspeed) + "; " + str(BR_Cadence) + "; " + str(HU_Cadence) + "; " + str(BR_Balance)  \
            + "; " + str(HU_Balance) + "; " + str(BR_Temp) + "; " + str(HU_Temp) + "; " + str(BR_Distance) + "; " + str(HU_Distance) \
            + "; " + str(BR_Pback) + "; " + str(HU_Pback) + "; " + format(BR_Alarm,'#018b') + "; " + format(HU_Alarm, '#018b') + "; " + str(HU_Res) \
            + "; " + str(BR_ResL) + "; " + str(BR_ResR) + "; " + str(BR_Res1) + "; " + str(BR_Res2) + "\n"

    try:
        fileLog.write(logText)
        fileLog.flush()
    except:
        print("WriteLog (" + logText + ") called, but file is not opened.")
        pass


# ==============================================================================
# Main program; Command line parameters
# ==============================================================================

#-------------------------------------------------------------------------------
# And go!
# ------------------------------------------------------------------------------
# input:        command line
#
# Description:  Show all dongles available
#               Open defined dongle
#               Start listening what's going on in the air
#
# Output:       Console/logfile
#
# Returns:      None
# ------------------------------------------------------------------------------

if True or debug.on(debug.Any):
    logfile.Open  ('BushidoBridge')
    logfile.Console ("Bushdo Bridge started")

    s = " %17s = %s"
    logfile.Console(s % ('BushidoBridge',  __version__ ))
    logfile.Console(s % ('antDongle', ant.__version__ ))

    clv.print()
    logfile.Console ("--------------------")

# ------------------------------------------------------------------------------
# First enumerate all dongles
# ------------------------------------------------------------------------------
ant.EnumerateAll()

# ------------------------------------------------------------------------------
# Open dongle; either the defined one or default
#
# Note, it does not matter which dongle you open.
# The dongle itself means a connection to the ANT+ network
# Each application starting can use any ANT+ dongle
# ------------------------------------------------------------------------------
if clv.dongle > 0:
    p = clv.dongle      # Specified on command line
else:
    p = None            # Take the default

AntDongle = ant.clsAntDongle(p)
logfile.Console (AntDongle.Message)

# Maybe these need to end up as command line arguments

# Pair the HU with the Bridge as master
PairHUwithBridge = False

# Configure the master channel - keep this under local control
masterDeviceNumber = clv.deviceNr
masterChannelID = 6

# Configure the slave channel - keep this under local control
slaveChannelID = 7
slaveDeviceNumber = 0  # Wildcard - number assigned by master

# HU
HUDeviceNumber = 0

# Following is for setting target power auto
simulatePower = True
# Up and down in the following power target range
minTarget = 150
maxTarget = 300
increment = 10
Weight = 10  # flywheel??
period = 10  # Increase/decrease in seconds

simulateSlope = False
if simulateSlope:
    minTarget = -5.0
    maxTarget =  5.0
    increment = 0.5
    Weight    = 82 # in this case athlete + bicycle weight
    simulatePower = False

Target = minTarget

# HU (paired as slave)
pairedHU = False

# Slave device on bridge paired
pairedAsSlave = True

# Master device on bridge paired
pairedAsMaster = False

# This is the main loop
while (AntDongle.OK):
    try:
        if (clv.bridgeHU):
            # Check traffic between BHU and TTS4 (paired with Brake)
            bridgeDeviceTypeID = ant.DeviceTypeID_BHU
        else:
            # Monitor traffic between BHU or TTS4 (paired with Bridge!!!!) and Brake
            bridgeDeviceTypeID = ant.DeviceTypeID_BSH

        bridgeNetworkNumber 	= 0x01
        bridgeRfFrequency 	= ant.RfFrequency_2460Mhz
        bridgeChannelPeriod 	= 0x1000
        bridgeTransmitPower	= ant.TransmitPower_0dBm

        # HU (pair as slave)
        if PairHUwithBridge: pairedHU = True # Not needed

        # slave device on bridge
        if PairHUwithBridge: pairedAsSlave = True # Not needed
        # Serial and version messages
        slaveSerialMsg  = ant.ComposeMessage(ant.msgID_BroadcastData, ant.msgPageAD01_TacxBushidoData(slaveChannelID, 2015, 2015))
        slaveSWmsg      = ant.ComposeMessage(ant.msgID_BroadcastData, ant.msgPageAD02_TacxBushidoData(slaveChannelID, 1, 2, 3456))

        # Serial and version messages
        masterSerialMsg = ant.ComposeMessage(ant.msgID_BroadcastData, ant.msgPageAD01_TacxBushidoData(masterChannelID, 2020, 2020))
        masterSWmsg     = ant.ComposeMessage(ant.msgID_BroadcastData, ant.msgPageAD02_TacxBushidoData(masterChannelID, 5, 6, 7890))

        # ----------------------------------------------------------------------
        # Reset and Calibrate ANT+ dongle
        # ----------------------------------------------------------------------
        AntDongle.ResetDongle()
        AntDongle.Calibrate()

        # ----------------------------------------------------------------------
        # Open channels
        # -----------------------------------------------------------------------
        welcome = ""

        # ----------------------------------------------------------------------
        # Get info from the devices
        # ----------------------------------------------------------------------
        logfile.Console("Listening, press Ctrl-C to exit")

        while not AntDongle.DongleReconnected:
            StartTime = time.time()

            if (not clv.bridgeHU): # Activate HU as master controlling brake
                logfile.Console(
                    'Configuring as slave BHU device %s on Bridge channel %s' % (0, ant.channel_VHU_s))
                messages = [
                    ant.msg42_AssignChannel(ant.channel_VHU_s, ant.ChannelType_BidirectionalReceive, 0x01),
                    ant.msg51_ChannelID(ant.channel_VHU_s, 0, ant.DeviceTypeID_BHU, 0),
                    ant.msg45_ChannelRfFrequency(ant.channel_VHU_s, bridgeRfFrequency),
                    ant.msg43_ChannelPeriod(ant.channel_VHU_s, bridgeChannelPeriod),
                    ant.msg60_ChannelTransmitPower(ant.channel_VHU_s, bridgeTransmitPower),
                    ant.msg4B_OpenChannel(ant.channel_VHU_s),
                    ant.msg4D_RequestMessage(ant.channel_VHU_s, ant.msgID_ChannelID)
                ]
                AntDongle.Write(messages)

                logfile.Console("Connecting to BHU as slave. This may take a while .....")

                #if DataPageNumber == 173 and SubPageNumber == 0x01:
                #    Mode, Year, DeviceNumber = ant.msgUnpage173_01_TacxBushidoSerialMode(info)
                iteration = 0
                while (not pairedHU):
                    # Pairing with HU - act as slave
                    iteration += 1

                    StartTime = time.time()
                    # -------------------------------------------------------------------
                    # Receive response from channels
                    # -------------------------------------------------------------------
                    data = AntDongle.Read(False)

                    for d in data:
                        synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                        # ---------------------------------------------------------------
                        # Check msgID_ChannelID found on  correct channel
                        # ---------------------------------------------------------------
                        if (Channel == ant.channel_VHU_s) and (id == ant.msgID_ChannelID):
                            # -----------------------------------------------------------
                            # Check if correct DeviceType is discovered with DeviceNumber assigned
                            # -----------------------------------------------------------
                            Channel, DeviceNumber, DeviceTypeID, TransmissionType = ant.unmsg51_ChannelID(info)
                            if DeviceTypeID == ant.DeviceTypeID_BHU:
                                if DeviceNumber:
                                    HUDeviceNumber = DeviceNumber
                                    logfile.Write("Bridge: found master HU device with number %6.6d on slave channel %2.2d" % (
                                    HUDeviceNumber,  ant.channel_VHU_s), True)
                                    pairedHU = True
                                    break
                                elif (iteration % 10 == 0):
                                    logfile.Console("%6s - HU device number not assigned yet." % iteration)

                    messages = []
                    if (not pairedHU):
                        msg = ant.msg4D_RequestMessage( ant.channel_VHU_s, ant.msgID_ChannelID)
                        messages.append(msg)
                    else:
                        pass # adapt messages later
                        # Send serial and version data
                        # messages.append(slaveSerialMsg)
                        # messages.append(slaveSWmsg)

                    # Write collected messages
                    AntDongle.Write(messages, False, False)

                    # -------------------------------------------------------
                    # WAIT So we do not cycle faster than 2 x per second
                    # -------------------------------------------------------
                    SleepTime = 0.5 - (time.time() - StartTime)
                    if SleepTime > 0:
                        time.sleep(SleepTime)
            else:
                welcome = " I N    H E A D   U N I T    M O D E ..."

            logfile.Console(
                'Configuring as master ANT+ device %s on Bridge channel %s' % (masterDeviceNumber, masterChannelID))
            messages = [
                ant.msg42_AssignChannel(masterChannelID, ant.ChannelType_BidirectionalTransmit, bridgeNetworkNumber),
                ant.msg51_ChannelID(masterChannelID, masterDeviceNumber, bridgeDeviceTypeID, ant.TransmissionType_IC),
                ant.msg45_ChannelRfFrequency(masterChannelID, bridgeRfFrequency),
                ant.msg43_ChannelPeriod(masterChannelID, bridgeChannelPeriod),
                ant.msg60_ChannelTransmitPower(masterChannelID, bridgeTransmitPower),
                ant.msg4B_OpenChannel(masterChannelID),
                ant.msg4D_RequestMessage(masterChannelID, ant.msgID_ChannelID)
            ]
            AntDongle.Write(messages)

            logfile.Console("Connecting as master.")
            while (not pairedAsMaster):
                # Connecting to slave device  - acting as a master
                StartTime = time.time()

                data = AntDongle.Read(False)

                for d in data:
                    synch, length, id, info, checksum, _rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                    if ((Channel == masterChannelID) and (id == ant.msgID_ChannelID)):
                        Channel, DeviceNumber, DeviceTypeID, TransmissionType = ant.unmsg51_ChannelID(info)
                        # -----------------------------------------------------------
                        # Check if correct  DeviceType is discovered
                        # -----------------------------------------------------------
                        if (DeviceTypeID == bridgeDeviceTypeID):
                            logfile.Write("ANT+ Bridge: connected as master %6.6d on channel %2.2d" % (DeviceNumber, Channel), True)
                            pairedAsMaster = True
                            break

                messages = []
                if (not pairedAsMaster):
                    msg = ant.msg4D_RequestMessage(masterChannelID, ant.msgID_ChannelID)
                    messages.append(msg)
                else:
                    # Send serial and version data
                    messages.append(masterSerialMsg)
                    messages.append(masterSWmsg)

                AntDongle.Write(messages, False, False)

                # -------------------------------------------------------
                # WAIT So we do not cycle faster than 2 x per second
                # -------------------------------------------------------
                SleepTime = 0.5 - (time.time() - StartTime)
                if SleepTime > 0:
                    time.sleep(SleepTime)

            # End of Master connection

            logfile.Console(
                'Configuring as slave ANT+ device %s on Bridge channel %s' % (slaveDeviceNumber, slaveChannelID))
            messages = [
                ant.msg42_AssignChannel(slaveChannelID, ant.ChannelType_BidirectionalReceive, bridgeNetworkNumber),
                ant.msg51_ChannelID(slaveChannelID, slaveDeviceNumber, bridgeDeviceTypeID, 0),
                ant.msg45_ChannelRfFrequency(slaveChannelID, bridgeRfFrequency),
                ant.msg43_ChannelPeriod(slaveChannelID, bridgeChannelPeriod),
                ant.msg60_ChannelTransmitPower(slaveChannelID, bridgeTransmitPower),
                ant.msg4B_OpenChannel(slaveChannelID)
            ]
            AntDongle.Write(messages, True, False)

            logfile.Console ("Connecting as slave - needs master device to be active ...")
            iteration = 0
            while (not pairedAsSlave):
                # Pairing with Brake - act as slave
                iteration += 1

                StartTime = time.time()
                # -------------------------------------------------------------------
                # Receive response from channels
                # -------------------------------------------------------------------
                data = AntDongle.Read(False)

                for d in data:
                    synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                    # ---------------------------------------------------------------
                    # Check msgID_ChannelID found on  correct channel
                    # ---------------------------------------------------------------
                    if (Channel == slaveChannelID) and (id == ant.msgID_ChannelID):
                        # -----------------------------------------------------------
                        # Check if correct DeviceType is discovered with DeviceNumber assigned
                        # -----------------------------------------------------------
                        Channel, DeviceNumber, DeviceTypeID, TransmissionType = ant.unmsg51_ChannelID(info)
                        if DeviceTypeID == bridgeDeviceTypeID:
                            if DeviceNumber:
                                slaveDeviceNumber = DeviceNumber
                                logfile.Write("Bridge: found master device with number %6.6d on slave channel %2.2d" % (slaveDeviceNumber, slaveChannelID), True)
                                pairedAsSlave = True
                                break
                            elif (iteration % 10 == 0): logfile.Console ("%6s - Device number not assigned yet." % iteration)

                messages = []
                if (not pairedAsSlave):
                    msg = ant.msg4D_RequestMessage(slaveChannelID, ant.msgID_ChannelID)
                    messages.append(msg)
                    if (HUDeviceNumber):  # Keep HU alive
                        info = ant.msgPage000_TacxVortexHU_StayAlive(ant.channel_VHU_s)
                        msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                        messages.append(msg)
                else:
                    # Send serial and version data
                    messages.append(slaveSerialMsg)
                    messages.append(slaveSWmsg)

                # Write collected messages
                AntDongle.Write(messages, False, False)

                # -------------------------------------------------------
                # WAIT So we do not cycle faster than 2 x per second
                # -------------------------------------------------------
                SleepTime = 0.5 - (time.time() - StartTime)
                if SleepTime > 0:
                    time.sleep(SleepTime)

            # Successful slave connection

            if debug.on(debug.Function):
                logfile.Write("Starting Bushido bridge .................." + welcome, True)

            # Reset odometer?
            # info = ant.msgPage172_TacxVortexHU_ChangeHeadunitMode(ant.channel_VHU_s, ant.VHU_ResetDistance)
            # msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
            # if clv.csvExport: WriteCsv(info, True)
            # data = AntDongle.Write([msg], True, False)

            # Endless loop repacking messages
            startTime = time.time()

            setMode = -1
            prevMode = -1

            if (True): # For exercising input to HU
                speed    = 50
                maxSpeed = 600
                minSpeed = speed
                speedInc = 1
                speedFactor = 0

                cadence    = 50
                cadenceInc = 0.1
                maxCadence = 100
                minCadence = cadence

                power      = 100
                maxPower   = 400
                powerInc   = 1
                minPower   = power

                balance    = 0
                maxBalance = 100
                balanceInc = 1
                minBalance = balance

                Alarm = 1
                period = 10
                info = genDataPageInfo(masterChannelID, 16, 0, 0, 0, 0, 0, 0, 0)
                AlarmMsg = ant.ComposeMessage(ant.msgID_BroadcastData, info)

                while True:
                    if (HUDeviceNumber):
                        if setMode != ant.VHU_Training:
                            logfile.Write("Configuring head unit ...", True)
                            if setMode == ant.VHU_PCmode:
                                requestMode = ant.VHU_TrainingPause
                            elif setMode == ant.VHU_TrainingPause:
                                requestMode = ant.VHU_Training
                            else:
                                requestMode = ant.VHU_PCmode

                        while (setMode != ant.VHU_Training):
                            info = ant.msgPage172_TacxVortexHU_ChangeHeadunitMode(ant.channel_VHU_s, requestMode)
                            msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                            if clv.csvExport: WriteCsv(info, True)
                            data = AntDongle.Write([msg], True, False)

                            for d in data:
                                synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                                SubPageNumber = info[2] if len(info) > 2 else None
                                # ---------------------------------------------------------------
                                # Check on response message
                                # ---------------------------------------------------------------
                                if Channel == ant.channel_VHU_s and id == ant.msgID_BroadcastData and DataPageNumber == 173 and SubPageNumber == 0x01:
                                    setMode, Year, DeviceNumber = ant.msgUnpage173_01_TacxBushidoSerialMode(info)
                                    if setMode == ant.VHU_PCmode:
                                        # PC connection active, go to training mode
                                        if prevMode != setMode:
                                            logfile.Write("... Connected", True)
                                            prevMode = setMode
                                        requestMode = ant.VHU_TrainingPause
                                    elif setMode == ant.VHU_TrainingPause:
                                        # entered training mode, start training
                                        if prevMode != setMode:
                                            logfile.Write("...... Paused", True)
                                            prevMode = setMode
                                        requestMode = ant.VHU_Training
                                    elif setMode == ant.VHU_Training:
                                        logfile.Write("......... Started", True)
                                        prevMode = setMode

                                        time.sleep(0.1)

                    now = time.time()
                    if (now - startTime) > period:
                        startTime = now
                        speedFactor = (1 + 2*random.random())/2
                        speed += speedInc
                        balance += balanceInc
                        cadence += cadenceInc
                        power += powerInc
                        if speed >= maxSpeed or speed <= minSpeed:
                            speedInc *= -1
                        if balance >= maxBalance or balance <= minBalance:
                            balanceInc *= -1
                        if cadence >= maxCadence or cadence <= minCadence:
                            cadenceInc *= -1
                        if power >= maxPower or power <= minPower:
                            powerInc *= -1

                        logfile.Write("................ Sending  0x%2.2x  .................."  % Alarm, True)
                        print ("Speed: %3.3d; Cadence: %3.3d; Balance: %3.3d; Power: %3.3d; Speedfactor %2.4f" % (speed, cadence, balance, power, speedFactor))

                        info = genDataPageInfo(masterChannelID, 16, Alarm, 0, 0, 0,  0, 0, 0)
                        AlarmMsg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                        #if Alarm < 8:
                        #    Alarm += 1
                        #elif Alarm < 128:
                        if Alarm < 128:
                            Alarm = Alarm << 1
                        else:
                            Alarm = 1

                    AntDongle.Write([AlarmMsg])
                    info = ant.msgPage02_TacxBushidoData(masterChannelID, speed, int(cadence), balance)
                    msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                    AntDongle.Write([msg])

                    info = ant.msgPage01_TacxBushidoData(masterChannelID, power)
                    msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                    AntDongle.Write([msg])

                    info = genDataPageInfo(masterChannelID, 4, 0, int(speed*speedFactor/10), 0, 0, 0, 0, 0)
                    msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                    data = AntDongle.Write([msg], True, False)
                    for d in data:
                        synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                        SubPageNumber = info[2] if len(info) > 2 else None
                        # ---------------------------------------------------------------
                        # Check on response message
                        # ---------------------------------------------------------------
                        if Channel == ant.channel_VHU_s and id == ant.msgID_BroadcastData and DataPageNumber == 173 and SubPageNumber == 0x01:
                            setMode, Year, DeviceNumber = ant.msgUnpage173_01_TacxBushidoSerialMode(info)

            while True:
                # To pair HU with Bridge as master enable the following
                if PairHUwithBridge:
                    AntDongle.Write([masterSerialMsg])
                    AntDongle.Write([masterSWmsg])
                else:
                    # Ensure head unit is on the right state
                    if (HUDeviceNumber):
                        if setMode != ant.VHU_Training:
                            logfile.Write("Configuring head unit ...", True)
                            if setMode   == ant.VHU_PCmode:         requestMode = ant.VHU_TrainingPause
                            elif setMode == ant.VHU_TrainingPause:  requestMode = ant.VHU_Training
                            else:                                   requestMode = ant.VHU_PCmode

                        while (setMode != ant.VHU_Training):
                            info = ant.msgPage172_TacxVortexHU_ChangeHeadunitMode(ant.channel_VHU_s, requestMode)
                            msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                            if clv.csvExport: WriteCsv(info, True)
                            data = AntDongle.Write([msg], True, False)

                            for d in data:
                                synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                                SubPageNumber = info[2] if len(info) > 2 else None
                                # ---------------------------------------------------------------
                                # Check on response message
                                # ---------------------------------------------------------------
                                if Channel == ant.channel_VHU_s and id == ant.msgID_BroadcastData and DataPageNumber == 173 and SubPageNumber == 0x01:
                                    setMode, Year, DeviceNumber = ant.msgUnpage173_01_TacxBushidoSerialMode(info)
                                    if setMode == ant.VHU_PCmode:
                                        # PC connection active, go to training mode
                                        if prevMode != setMode:
                                            logfile.Write("... Connected", True)
                                            prevMode = setMode
                                        requestMode = ant.VHU_TrainingPause
                                    elif setMode == ant.VHU_TrainingPause:
                                        # entered training mode, start training
                                        if prevMode != setMode:
                                            logfile.Write("...... Paused", True)
                                            prevMode = setMode
                                        requestMode = ant.VHU_Training
                                    elif setMode == ant.VHU_Training:
                                        logfile.Write("......... Started", True)
                                        prevMode = setMode

                                        time.sleep(0.1)

                    logDataChanged = False
                    counter = 0
                    data = AntDongle.Read(False)
                    logfile.Write("................ Read %3.3d messages from Dongle.................." % len(data))
                    for d in data:
                        synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                        SubPageNumber = info[2] if len(info) > 2 else None

                        #====================================================================================
                        # Decode datapages for Bushido 1980 case
                        #====================================================================================
                        if id == ant.msgID_BroadcastData or id == ant.msgID_AcknowledgedData:
                            # ---------------------------------------------------------------
                            # Data page x00 - with TTS only - when underspeeding?
                            # ---------------------------------------------------------------
                            if DataPageNumber == 0:
                                ant.msgUnpage00_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info, True)

                            # ---------------------------------------------------------------
                            # Data page 01 - Power from brake
                            # ---------------------------------------------------------------
                            elif (DataPageNumber == 1 and Channel == slaveChannelID):
                                Power, ResL, ResR = ant.msgUnpage01_TacxBushidoData(info)
                                if (Power != BR_Power):
                                    BR_Power = Power
                                    logDataChanged = True
                                if (ResL != BR_ResL):
                                    BR_ResL = ResL
                                    logDataChanged = True
                                if (ResR != BR_ResR):
                                    BR_ResR = ResR
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page 01 target power from BHU
                            # ---------------------------------------------------------------
                            elif (DataPageNumber == 1 and Channel == masterChannelID):
                                Resistance = ant.msgUnpage01_TacxBushidoHeadDataPower(info)
                                if (Resistance != HU_Res):
                                    HU_Res = Resistance
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page 02 - Speed, Cadence, and Balance
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 2:
                                Speed, Cadence, Balance = ant.msgUnpage02_TacxBushidoData(info)
                                if (Speed != BR_Speed):
                                    BR_Speed = Speed
                                    logDataChanged = True
                                if (Cadence != BR_Cadence):
                                    BR_Cadence = Cadence
                                    logDataChanged = True
                                if (Balance != BR_Balance):
                                    BR_Balance = Balance
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page 04 - single field speed, resistance numbers?
                            # pass for the time being
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 4:
                                Vspeed, Res1, Res2 = ant.msgUnpage04_TacxBushidoData(info)

                                if (Vspeed != BR_Vspeed):
                                    BR_Vspeed = Vspeed
                                    logDataChanged = True
                                if (Res1 != BR_Res1):
                                    BR_Res1 = Res1
                                    logDataChanged = True
                                if (Res2 != BR_Res2):
                                    BR_Res2 = Res2
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page 08 - Counter (odometer) - pass
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 8:
                                Distance = ant.msgUnpage08_TacxBushidoData(info)
                                if (Distance != BR_Distance):
                                    BR_Distance = Distance
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page 16 - Brake Status
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 16:
                                Alarm, Temperature = ant.msgUnpage10_TacxBushidoData(info)
                                if (Alarm != BR_Alarm):
                                    BR_Alarm = Alarm
                                    logDataChanged = True
                                if (Temperature != BR_Temp):
                                    BR_Temp = Temperature
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page x22 - from brake when calibrating
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 34:
                                powerback = ant.msgUnpage22_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info, True)
                                if (Powerback != BR_Pback):
                                    BR_Pback = Powerback
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page x23 - from HU when calibrating
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 35:
                                ant.msgUnpage23_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info, True)

                            # ---------------------------------------------------------------
                            # Data page xac heartbeat pages, don't bother
                            # ---------------------------------------------------------------
                            elif (DataPageNumber == 172):
                                if clv.csvExport: WriteCsv(info, True)

                            # ---------------------------------------------------------------
                            # Data page xad msgUnpage173_TacxBushidoData
                            # Serial number and SW version
                            # ---------------------------------------------------------------
                            elif (DataPageNumber == 173):
                                if Channel == ant.channel_VHU_s and SubPageNumber == 1:
                                    setMode, Year, Number = ant.msgUnpage173_01_TacxBushidoSerialMode(info)
                                elif SubPageNumber == 2:
                                    ant.msgUnpageAD02_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info, True)

                            elif DataPageNumber == 221:
                                # Data pages from HU
                                if Channel == ant.channel_VHU_s:
                                    # -------------------------------------------------------------------
                                    # Data page 221 (0x10) msgUnpage221_TacxVortexHU_ButtonPressed
                                    # -------------------------------------------------------------------
                                    if id == ant.msgID_AcknowledgedData and SubPageNumber == 0x10:
                                        Buttons = ant.msgUnpage221_TacxVortexHU_ButtonPressed(info)
                                        if clv.csvExport: WriteCsv(info, True)
                                        if debug.on(debug.Function):
                                            logfile.Write('Bushido Page=%d/%#x (IN)  Keycode=%d' %
                                                          (DataPageNumber, SubPageNumber, Buttons), True)
                                    elif id == ant.msgID_BroadcastData:
                                        if SubPageNumber == 1:
                                            Power, Speed, Cadence, Balance = ant.msgUnpage221_01_TacxGeniusSpeedPowerCadence(info)
                                            if (Power != HU_Power):
                                                HU_Power = Power
                                                logDataChanged = True
                                            if (Speed != HU_Speed):
                                                HU_Speed = Speed
                                                logDataChanged = True
                                            if (Cadence != HU_Cadence):
                                                HU_Cadence = Cadence
                                                logDataChanged = True
                                            if (Balance != HU_Balance):
                                                HU_Balance = Balance
                                                logDataChanged = True

                                        elif SubPageNumber == 2:
                                            Distance, Heartrate = ant.msgUnpage221_02_TacxGeniusDistanceHR(info)
                                            if (Distance != HU_Distance):
                                                HU_Distance = Distance
                                                logDataChanged = True

                                        elif SubPageNumber == 3:
                                            Alarm, Temperature, Powerback = ant.msgUnpage221_03_TacxGeniusAlarmTemperature(info)
                                            if (Alarm != HU_Alarm):
                                                HU_Alarm = Alarm
                                                logDataChanged = True
                                            if (Temperature != HU_Temp):
                                                HU_Temp = Temperature
                                                logDataChanged = True
                                            if (Powerback != HU_Pback):
                                                HU_Pback= Powerback
                                                logDataChanged = True

                                        elif SubPageNumber == 4:
                                            CalibrationState, CalibrationValue = ant.msgUnpage221_04_TacxGeniusCalibrationInfo(info)
                                            if clv.csvExport: WriteCsv(info, True)

                                else:
                                    # ---------------------------------------------------------------
                                    # Data page xdd msgUnpage173_TacxBushidoData
                                    # Pages from HU
                                    # ---------------------------------------------------------------
                                    ant.msgUnpageDD_TacxBushidoData(info)
                                    if clv.csvExport: WriteCsv(info, True)

                            else:
                                if (Channel == slaveChannelID):
                                    logfile.Write("=================== Slave channel: unhandled Date Page %3.3d" % DataPageNumber, True)
                                else:
                                    logfile.Write("=================== Master channel: unhandled Date Page %3.3d" % DataPageNumber, True)

                        # Actual message conversion here - after decodoing incoming
                        ab = bytearray(info)
                        if (id == ant.msgID_ChannelResponse and (int(ab[1]) == 1)):
                            # Do not re-transit RF response messages
                            pass
                        elif (id == ant.msgID_BroadcastData and DataPageNumber == 173):
                            # Do not forward serial and SW but use our own instead so know what to pair (avoid bridge bypass)
                            if (Channel == slaveChannelID):
                                if      int(info[2]) == 1:    AntDongle.Write([masterSerialMsg])    # sub page 1
                                elif    int(info[2]) == 2:    AntDongle.Write([masterSWmsg])        # sub page 2
                            elif (Channel == masterChannelID):
                                if      int(info[2]) == 1:    AntDongle.Write([slaveSerialMsg])     # sub page 1
                                elif    int(info[2]) == 2:    AntDongle.Write([slaveSWmsg])         # sub page 2
                        elif Channel == slaveChannelID or Channel == masterChannelID:
                            if Channel == slaveChannelID:
                                ab[0] = masterChannelID
                            else:
                                ab[0] = slaveChannelID
                            info = bytes(ab)
                            msg = ant.ComposeMessage(id, info)
                            AntDongle.Write([msg], False)
                            counter += 1
                        elif Channel == ant.channel_VHU_s: pass # not to be forwarded
                        else:
                            logfile.Console("Message ID %2.2x found on channel %2.2d - not forwarded" % (id, Channel))

                    logfile.Write("................ Bridged %3.3d messages .................." % counter)

                    now = time.time()
                    if (now - startTime) > period:
                        startTime = now
                        if (simulatePower or simulateSlope):
                            if simulatePower:
                                logfile.Write("................ Setting power target to %3.3d  .................." % Target, True)
                                info = ant.msgPageDC_TacxBushidoDataPower(ant.channel_VHU_s, Target, Weight)
                            elif simulateSlope:
                                logfile.Write("................ Setting grade target to %4.2f percent  .................." % Target, True)
                                info = ant.msgPageDC_TacxBushidoDataSlope(ant.channel_VHU_s, Target, Weight)

                            HU_Target = Target
                            logDataChanged = True

                            msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                            AntDongle.Write([msg], False, False)

                            Target += increment
                            if (Target >= maxTarget or Target <= minTarget):
                                increment *= -1

                        else:
                            logfile.Write("................ Not simulating a training  ..................", True)

                    if (logDataChanged):
                        WriteLog(not simulateSlope)



    except KeyboardInterrupt:
        logfile.Console ("Listening stopped")

    except Exception as e:
        logfile.Console ("Listening stopped due to exception: " + str(e))

    #---------------------------------------------------------------
    # Free channel
    #---------------------------------------------------------------
    messages = []

    messages.append ( ant.msg41_UnassignChannel(slaveChannelID) )
    messages.append ( ant.msg41_UnassignChannel((masterChannelID) ) )

    AntDongle.Write(messages)

    #---------------------------------------------------------------
    # Release dongle
    #-----------------------------------------------------------------------
    AntDongle.ResetDongle ()
    #---------------------------------------------------------------------------
    # Quit "while AntDongle.OK"
    #---------------------------------------------------------------------------
    if AntDongle.DongleReconnected:
        AntDongle.ApplicationRestart()
    else:
        break
    logfile.Console ("We're done")
    logfile.Console ("--------------------")
    # To be added at the end

    if clv.csvExport:
        csvFile.close()
        fileLog.close()


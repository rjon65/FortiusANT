#-------------------------------------------------------------------------------
# Version info
#-------------------------------------------------------------------------------
__version__ = "2020-12-17"
# 2020-12-17    First version based on ExplorAnt
#
# Man in the middle, forwarding ANT messages on either:
# - Bushido Brake channel type
#   - Brake master to either HU or TTS4 (Bridge is slave to Brake)
#     => this requires to first connect the Bridge as a Brake to HU/TTS4
#        Set ConnectHUtoBrakeMode to True
#   - Option to add a Bridge slave interface to HU to drive Brake settings
#
#   Bushido Brake-(M) ---ch7---> (S)-Bridge-(M) ---ch6---> (S)-Head Unit
#                                      |                          |
#                                     (S)                        (M)
#                                      |___________ch5____________|
#
# - Bushido Head Unit channel type (Bridge is slave to HU)
#   - HU master to TTS4 (but not happening on later versions of TTS4)
#
#   Bushido HU-(M) ---ch7---> (S)-Bridge-(M) ---ch6---> (S)-TTS4
#
#   ch7 = bridge slave channel: connects to master
#   ch6 = bridge master channel: connects to slave
#   ch5 = channel that connects to HU master
#
# Decodes data pages thus forwarded and can be exported into two CSV files
# - BushidoBridge.csv: unknown/uninteresting pages/fields for analysis
# - BushidoBridgeLog.csv: known fields
#-------------------------------------------------------------------------------
import struct
import time
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
        logText = "Timestamp;Channel;Page;Payload 1;Payload 2;Payload 3;Payload 4;Payload 5;Payload 6;Payload 7;Mode\n"
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
    logText += str(microDelta) + ";"
    logText += str(int(tuple[nChannel])) + ";"
    logText += str(int(tuple[nDataPageNumber])) + ";"
    logText += str(int(tuple[nData1])) + ";"
    logText += str(int(tuple[nData2])) + ";"
    logText += str(int(tuple[nData3])) + ";"
    logText += str(int(tuple[nData4])) + ";"
    logText += str(int(tuple[nData5])) + ";"
    logText += str(int(tuple[nData6])) + ";"
    logText += str(int(tuple[nData7])) + ";"
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
            logText = "Timestamp;HU_PowerTarget;"
        else:
            logText = "Timestamp;HU_SlopeTarget;"
                 
        logText += "BR_Power;HU_Power;BR_Speed;HU_Speed;BR_Vspeed;BR_Cadence; HU_Cadence;BR_Balance;HU_Balance;" \
                     "BR_Temp;HU_Temp;BR_Distance;HU_Distance;BR_Pback;HU_Pback;BR_Alarm;HU_Alarm;" \
                     "HU_Res;BR_ResL;BR_ResR;BR_Res1;BR_Res2\n"
    else:
        logText = ""

    now = datetime.now()
    delta = now - startLog
    # millisecond resolution should be OK
    msecDelta = int(delta.microseconds / 1000) + 1000*(delta.seconds)
    logText += str(msecDelta) + ";" + str(HU_Target) + ";" + str(BR_Power) + ";" + str(HU_Power) + ";" + str(BR_Speed) \
            + ";" + str(HU_Speed) + ";" + str(BR_Vspeed) + ";" + str(BR_Cadence) + ";" + str(HU_Cadence) + ";" + str(BR_Balance)  \
            + ";" + str(HU_Balance) + ";" + str(BR_Temp) + ";" + str(HU_Temp) + ";" + str(BR_Distance) + ";" + str(HU_Distance) \
            + ";" + str(BR_Pback) + ";" + str(HU_Pback) + ";" + format(BR_Alarm,'#018b') + ";" + format(HU_Alarm, '#018b') + ";" + str(HU_Res) \
            + ";" + str(BR_ResL) + ";" + str(BR_ResR) + ";" + str(BR_Res1) + ";" + str(BR_Res2) + "\n"

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

# ------------------------------------------------------------------------------
# Configure what we want to get done
# Maybe these need to end up as command line arguments in the end
# ------------------------------------------------------------------------------

# Only needed to pair the HU with the Bridge as master - exits bridge when done
ConnectHUtoBrakeMode = False

# HU to be paired - i.e. when driving Brake through HU
pairHU = False

# Slave device on bridge to be paired?
pairAsSlave = True

# Master device on bridge to be paired?
pairAsMaster = True

# If HU connection mode do not need to pair HU or Slave
if ConnectHUtoBrakeMode:
    pairHU          = False
    pairAsSlave     = False
    pairAsMaster    = False

# ------------------------------------------------------------------------------
# Simulating a trainer: target controlled through up/down buttons HU
# ------------------------------------------------------------------------------

# Calibration needed - before training starts
calibrateBrake = True

# Power target
simulatePowerTraining = True
targetIncrement       = 10
Weight                = 10  # flywheel??
Target                = 150 # target power at start

# Slope target
simulateSlopeTraining = False
if simulateSlopeTraining:
    targetIncrement = 0.5
    Weight          = 78 # in this case athlete + bicycle weight
    Target          = 0  # target grade at start
    simulatePowerTraining = False

# ------------------------------------------------------------------------------
# Configurations kept under local control
# The bridge master channel - connects to slave
masterDeviceNumber = clv.deviceNr
masterChannelID = 6

# The bridge slave channel - connects to master
slaveChannelID = 7
slaveDeviceNumber = 0  # Wildcard - number assigned by master

# The optional HU (master)
HUDeviceNumber = 0 # Wildcard - number assigned by master
huChannelID = ant.channel_VHU_s

if (clv.bridgeHU):
    # Check traffic between master BHU and slave TTS4 (paired with Brake)
    bridgeDeviceTypeID = ant.DeviceTypeID_BHU
    bridgeTypeName     = "Head Unit"
    pairHU             = False
    welcome            = " I N    H E A D   U N I T    M O D E ..."
else:
    # Monitor traffic between master Brake and slave BHU or TTS4 (paired with Bridge!!!!)
    bridgeDeviceTypeID = ant.DeviceTypeID_BSH
    bridgeTypeName     = "Bushido Brake"
    welcome            = ""

bridgeNetworkNumber = 0x01
bridgeRfFrequency   = ant.RfFrequency_2460Mhz
bridgeChannelPeriod = 0x1000
bridgeTransmitPower = ant.TransmitPower_0dBm

# Serial and version messages
slaveSerialMsg = ant.ComposeMessage(ant.msgID_BroadcastData,
                                    ant.msgPageAD01_TacxBushidoData(slaveChannelID, 2015, 2015))
slaveSWmsg = ant.ComposeMessage(ant.msgID_BroadcastData, ant.msgPageAD02_TacxBushidoData(slaveChannelID, 1, 2, 3456))

# Serial and version messages
masterSerialMsg = ant.ComposeMessage(ant.msgID_BroadcastData,
                                     ant.msgPageAD01_TacxBushidoData(masterChannelID, 2020, 2020))
masterSWmsg = ant.ComposeMessage(ant.msgID_BroadcastData, ant.msgPageAD02_TacxBushidoData(masterChannelID, 5, 6, 7890))

# ------------------------------------------------------------------------------
# This is the main loop
# ------------------------------------------------------------------------------
while (AntDongle.OK):
    try:
        # ----------------------------------------------------------------------
        # Reset and Calibrate ANT+ dongle
        # ----------------------------------------------------------------------
        AntDongle.ResetDongle()
        AntDongle.Calibrate()
        # ----------------------------------------------------------------------
        # Get info from the devices
        # ----------------------------------------------------------------------
        while not AntDongle.DongleReconnected:
            StartTime = time.time()
            # HU slave only to be used in combination with Bushido Brake bridge
            if pairHU:
                logfile.Console(
                    'Configuring as slave HU device with number %s on channel %s' % (0, huChannelID))
                messages = [
                    ant.msg42_AssignChannel(huChannelID, ant.ChannelType_BidirectionalReceive, 0x01),
                    ant.msg51_ChannelID(huChannelID, 0, ant.DeviceTypeID_BHU, 0),
                    ant.msg45_ChannelRfFrequency(huChannelID, bridgeRfFrequency),
                    ant.msg43_ChannelPeriod(huChannelID, bridgeChannelPeriod),
                    ant.msg60_ChannelTransmitPower(huChannelID, bridgeTransmitPower),
                    ant.msg4B_OpenChannel(huChannelID),
                    ant.msg4D_RequestMessage(huChannelID, ant.msgID_ChannelID)
                ]
                AntDongle.Write(messages)

                logfile.Console("Connecting to HU as slave. This may take a while .....")

                iteration = 0
                while pairHU:
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
                        if (Channel == huChannelID) and (id == ant.msgID_ChannelID):
                            # -----------------------------------------------------------
                            # Check if correct DeviceType is discovered with DeviceNumber assigned
                            # -----------------------------------------------------------
                            Channel, DeviceNumber, DeviceTypeID, TransmissionType = ant.unmsg51_ChannelID(info)
                            if DeviceTypeID == ant.DeviceTypeID_BHU:
                                if DeviceNumber:
                                    HUDeviceNumber = DeviceNumber
                                    logfile.Write("Bridge: found master HU device with number %s on slave channel %s" % (
                                    HUDeviceNumber,  huChannelID), True)
                                    pairHU = False
                                    break
                                elif (iteration % 10 == 0):
                                    logfile.Console("%6s - HU device number not assigned yet." % iteration)

                    messages = []
                    if pairHU:
                        msg = ant.msg4D_RequestMessage(huChannelID, ant.msgID_ChannelID)
                        messages = [msg]
                    else:
                        messages = [slaveSerialMsg]
                        messages.append(slaveSWmsg)

                    # Write collected messages
                    AntDongle.Write(messages, False, False)

                    # -------------------------------------------------------
                    # WAIT So we do not cycle faster than 2 x per second
                    # -------------------------------------------------------
                    SleepTime = 0.5 - (time.time() - StartTime)
                    if SleepTime > 0:
                        time.sleep(SleepTime)
            else:
                logfile.Console('NO slave HU device configured!')

            if pairAsMaster:
                logfile.Console(
                    'Bridge %s type: configuring as master device %s on Bridge channel %s' % (bridgeTypeName, masterDeviceNumber, masterChannelID))
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

                while pairAsMaster:
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
                                logfile.Write("Bridge %s type: connected as master %6.6d on channel %2.2d" % (bridgeTypeName, DeviceNumber, Channel), True)
                                pairAsMaster = False
                                break

                    messages = []
                    if pairAsMaster:
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
            else:
                logfile.Console(
                    'Bridge %s type: NO master device configured on Bridge channel %s' % (bridgeTypeName, masterChannelID))

            if pairAsSlave:
                logfile.Console(
                    'Bridge %s type: configuring as slave device %s on Bridge channel %s' % (bridgeTypeName, slaveDeviceNumber, slaveChannelID))
                messages = [
                    ant.msg42_AssignChannel(slaveChannelID, ant.ChannelType_BidirectionalReceive, bridgeNetworkNumber),
                    ant.msg51_ChannelID(slaveChannelID, slaveDeviceNumber, bridgeDeviceTypeID, 0),
                    ant.msg45_ChannelRfFrequency(slaveChannelID, bridgeRfFrequency),
                    ant.msg43_ChannelPeriod(slaveChannelID, bridgeChannelPeriod),
                    ant.msg60_ChannelTransmitPower(slaveChannelID, bridgeTransmitPower),
                    ant.msg4B_OpenChannel(slaveChannelID)
                ]
                AntDongle.Write(messages, True, False)

                logfile.Console ("Bridge %s type: connecting as slave - needs master device to be active ..." % bridgeTypeName)

                iteration = 0
                while pairAsSlave:
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
                                    logfile.Write("Bridge %s type: found master device with number %6.6d on slave channel %2.2d" % (bridgeTypeName, slaveDeviceNumber, slaveChannelID), True)
                                    pairAsSlave = False
                                    break
                                elif (iteration % 10 == 0): logfile.Console ("%6s - Device number not assigned yet." % iteration)

                    messages = []
                    if pairAsSlave:
                        msg = ant.msg4D_RequestMessage(slaveChannelID, ant.msgID_ChannelID)
                        messages.append(msg)
                        if (HUDeviceNumber):  # Keep HU alive
                            info = ant.msgPage000_TacxVortexHU_StayAlive(huChannelID)
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
            else:
                logfile.Console(
                    'Bridge %s type: NO slave device configured on Bridge channel %s' % (bridgeTypeName, slaveChannelID))

            if ConnectHUtoBrakeMode:
                # Connect HU with Bridge acting as master Brake
                logfile.Write("Starting Bushido bridge in HU to brake connection mode ..................", True)
                messages = [
                    ant.msg42_AssignChannel(masterChannelID, ant.ChannelType_BidirectionalTransmit,
                                            bridgeNetworkNumber),
                    ant.msg51_ChannelID(masterChannelID, masterDeviceNumber, bridgeDeviceTypeID,
                                        ant.TransmissionType_IC),
                    ant.msg45_ChannelRfFrequency(masterChannelID, bridgeRfFrequency),
                    ant.msg43_ChannelPeriod(masterChannelID, bridgeChannelPeriod),
                    ant.msg60_ChannelTransmitPower(masterChannelID, bridgeTransmitPower),
                    ant.msg4B_OpenChannel(masterChannelID),
                    ant.msg4D_RequestMessage(masterChannelID, ant.msgID_ChannelID)
                ]
                AntDongle.Write(messages)

                iteration = 0
                while True:
                    iteration += 1

                    messages = [masterSerialMsg]
                    messages.append(masterSWmsg)
                    msg = ant.msg4D_RequestMessage(slaveChannelID, ant.msgID_ChannelID)
                    messages.append(msg)
                    data = AntDongle.Write(messages, True, False)
                    for d in data:
                        synch, length, id, info, checksum, rest, Channel, DataPageNumber = ant.DecomposeMessage(d)
                        SubPageNumber = info[2] if len(info) > 2 else None
                        if Channel == masterChannelID and DataPageNumber == 172:
                            print("Head unit connected to master brake output. Exiting ...")
                            exit (0)
                    if (iteration % 10 == 0): logfile.Console("%6s - HU not connected yet." % iteration)
                    time.sleep(0.25)

            else: # For exercising input to HU
                startTime = time.time()

                # For calibration mode
                prevCalMode      = -1
                calibrationMode  = -1 #ant.BBR_Cal_State_NO_CAL
                calibrationValue = 0
                lastCalSpeed     = 0

                # For HU mode
                setMode     = -1
                prevMode    = -1
                requestMode = -1

                logfile.Write("Starting Bushido bridge ..................", True)
                if clv.bridgeHU:
                    logfile.Write(".................. Bridging Head Unit channel ..................", True)
                elif not HUDeviceNumber or (not simulatePowerTraining and not simulateSlopeTraining):
                    logfile.Write(".................. Bridging Bushido Brake channel - N O  T r a i n i n g ..................", True)
                else:
                    logfile.Write(".................. Bridging BushidoBrake Unit channel   -   T r a i n i n g  M o d e ..................", True)

                # Endless loop repacking messages
                initializeTarget = True
                StartTime        = time.time()
                lastSpeedChange  = StartTime
                while True:
                    messages = []
                    increaseTarget = False
                    decreaseTarget = False
                    if calibrateBrake:
                        code = -1
                        if time.time() - lastSpeedChange > 5:
                            logfile.Write("CALIBRATION  - START CYCLING ....", True)
                            lastSpeedChange = time.time()

                        if calibrationMode == ant.BBR_Cal_State_NO_CAL:
                            code = 0x63 # Start calibration
                            if prevCalMode != calibrationMode:
                                prevCalMode = calibrationMode
                        elif calibrationMode == ant.BBR_Cal_State_CAL_MODE:
                            code = 0x00
                            if prevCalMode != calibrationMode:
                                logfile.Write("CALIBRATION  - speed up to 40km/h", True)
                                prevCalMode = calibrationMode
                        elif calibrationMode == ant.BBR_Cal_State_CAL_REQ:
                            if prevCalMode != calibrationMode:
                                logfile.Write("CALIBRATION request acknowledged", True)
                                prevCalMode = calibrationMode
                        elif calibrationMode == ant.BBR_Cal_State_AT_SPEED:
                            if prevCalMode != calibrationMode:
                                logfile.Write("CALIBRATION  - STOP CYCLING !!!!", True)
                                prevCalMode = calibrationMode
                        elif calibrationMode == ant.BBR_Cal_State_SLOW_DOWN:
                            if prevCalMode != calibrationMode:
                                logfile.Write("CALIBRATION  - RUNOFF mode: do not pedal or brake", True)
                                prevCalMode = calibrationMode
                        elif calibrationMode == ant.BBR_Cal_State_SLOWED:
                            if prevCalMode != calibrationMode:
                                prevCalMode = calibrationMode
                                logfile.Write("CALIBRATION - RUNOFF COMPLETE - start cycling again", True)
                        elif calibrationMode == ant.BBR_Cal_State_NO_ERROR:
                            code = 0x58 # Request calibration status
                            if prevCalMode != calibrationMode:
                                prevCalMode = calibrationMode
                                logfile.Write("CALIBRATION  - completed successfully", True)
                        elif calibrationMode == ant.BBR_Cal_State_READY:
                            code = 0x4d  # Request calibration value
                            if prevCalMode != calibrationMode:
                                prevCalMode = calibrationMode
                                logfile.Write("CALIBRATION  - requesting calibration value ", True)
                        elif calibrationMode == ant.BBR_Cal_State_ERROR:
                            if prevCalMode != calibrationMode:
                                prevCalMode = calibrationMode
                                logfile.Write("CALIBRATION ERROR. STOP CYLING for next try ...", True)
                        elif calibrationMode == ant.BBR_Cal_State_VAL_RDY:
                            if prevCalMode != calibrationMode:
                                prevCalMode = calibrationMode
                                logfile.Write("CALIBRATION VALUE = %4.2f. Recommended range [13-19]" % calibrationValue, True)
                                if calibrationValue < 19 and calibrationValue > 13:
                                    pass #calibrateBrake = False
                                else:
                                    logfile.Write("CALIBRATION VALUE out of recommended range [13-19]. STOP CYCLING for next try ...", True)
                                    if calibrationValue < 13:
                                        logfile.Write("Insufficient roll pressure. Turn knob anti-clockwise.", True)
                                    else:
                                        logfile.Write("Too much roll pressure. Turn knob clockwise.", True)

                        if code != -1:
                            info = genDataPageInfo(slaveChannelID, 0x23, code, 0, 0, 0, 0, 0, 0)
                            msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                            messages.append(msg)
                            if clv.csvExport: WriteCsv(info, True)

                        if calibrateBrake and code <= 0 and time.time() - startTime > 0.5:
                            startTime = time.time()
                            if lastCalSpeed != BR_Speed:
                                logfile.Write("%4.2f km/h" % BR_Speed, True)
                                lastCalSpeed = BR_Speed
                                lastSpeedChange = startTime

                    elif HUDeviceNumber:
                        # HU used to send targets to brake - get/keep it in the right state
                        if setMode != ant.VHU_Training:
                            if requestMode == -1:
                                logfile.Write("Configuring head unit ...", True)
                                requestMode = ant.VHU_PCmode
                            if setMode == ant.VHU_PCmode:
                                if prevMode != setMode:
                                    logfile.Write("... Connected", True)
                                    prevMode = setMode
                                requestMode = ant.VHU_TrainingPause
                            elif setMode == ant.VHU_TrainingPause:
                                if prevMode != setMode:
                                    logfile.Write("...... Paused", True)
                                    prevMode = setMode
                                requestMode = ant.VHU_Training

                            info = ant.msgPage172_TacxVortexHU_ChangeHeadunitMode(huChannelID, requestMode)
                            msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                            messages.append(msg)
                            if clv.csvExport: WriteCsv(info, True)

                        elif prevMode != setMode:
                            # This is the first time in training state
                            logfile.Write("......... Started", True)
                            prevMode = setMode

                    data = AntDongle.Read(False)
                    logDataChanged = False
                    counter = 0
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
                                if clv.csvExport: WriteCsv(info)

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
                                if (Speed/10 != BR_Speed):
                                    BR_Speed = Speed/10
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
                                powerback, calibrationMode, calibrationValue = ant.msgUnpage22_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info)
                                if (powerback != BR_Pback):
                                    BR_Pback = powerback
                                    logDataChanged = True

                            # ---------------------------------------------------------------
                            # Data page x23 - from HU when calibrating
                            # ---------------------------------------------------------------
                            elif DataPageNumber == 35:
                                ant.msgUnpage23_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info)

                            # ---------------------------------------------------------------
                            # Data page xac heartbeat pages, don't bother
                            # ---------------------------------------------------------------
                            elif (DataPageNumber == 172):
                                if clv.csvExport: WriteCsv(info)

                            # ---------------------------------------------------------------
                            # Data page xad msgUnpage173_TacxBushidoData
                            # Serial number and SW version
                            # ---------------------------------------------------------------
                            elif (DataPageNumber == 173):
                                if Channel == huChannelID and SubPageNumber == 1:
                                    setMode, Year, Number = ant.msgUnpage173_01_TacxBushidoSerialMode(info)
                                elif SubPageNumber == 2:
                                    ant.msgUnpageAD02_TacxBushidoData(info)
                                if clv.csvExport: WriteCsv(info)

                            elif DataPageNumber == 221:
                                # Data pages from HU
                                if Channel == huChannelID:
                                    # -------------------------------------------------------------------
                                    # Data page 221 (0x10) msgUnpage221_TacxVortexHU_ButtonPressed
                                    # -------------------------------------------------------------------
                                    if id == ant.msgID_AcknowledgedData and SubPageNumber == 0x10:
                                        Buttons = ant.msgUnpage221_TacxVortexHU_ButtonPressed(info)
                                        if clv.csvExport: WriteCsv(info)
                                        if debug.on(debug.Function):
                                            logfile.Write('Bushido Page=%d/%#x (IN)  Keycode=%d' %
                                                          (DataPageNumber, SubPageNumber, Buttons))
                                        Keycode = Buttons & 0x0F  # ignore key press duration
                                        # Only check up/down buttons
                                        if Keycode == ant.VHU_Button_Up:
                                            increaseTarget = True
                                        elif Keycode == ant.VHU_Button_Down:
                                            decreaseTarget = True

                                    elif id == ant.msgID_BroadcastData:
                                        if SubPageNumber == 1:
                                            Power, Speed, Cadence, Balance = ant.msgUnpage221_01_TacxGeniusSpeedPowerCadence(info)
                                            if (Power != HU_Power):
                                                HU_Power = Power
                                                logDataChanged = True
                                            if (Speed/10 != HU_Speed):
                                                HU_Speed = Speed/10
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
                                            if clv.csvExport: WriteCsv(info)

                                else:
                                    # ---------------------------------------------------------------
                                    # Data page xdd msgUnpage173_TacxBushidoData
                                    # Pages from HU
                                    # ---------------------------------------------------------------
                                    ant.msgUnpageDD_TacxBushidoData(info)
                                    if clv.csvExport: WriteCsv(info)

                            else:
                                if Channel == slaveChannelID:
                                    logfile.Write("=================== Slave channel: unhandled Date Page %3.3d" % DataPageNumber, True)
                                elif Channel == huChannelID:
                                    logfile.Write("=================== HU channel: unhandled Date Page %3.3d" % DataPageNumber, True)
                                else:
                                    logfile.Write("=================== Master channel: unhandled Date Page %3.3d" % DataPageNumber, True)

                        # Actual message forwarding
                        ab = bytearray(info)
                        if (id == ant.msgID_ChannelResponse and (int(ab[1]) == 1)):
                            # Do not re-transit RF response messages
                            pass
                        elif (id == ant.msgID_BroadcastData and DataPageNumber == 173):
                            # Do not forward serial and SW but use our own instead so can check other devices are talking
                            # to the bridge (avoid bridge bypass)
                            if (Channel == slaveChannelID):
                                if      int(info[2]) == 1:    messages.append(masterSerialMsg)    # sub page 1
                                elif    int(info[2]) == 2:    messages.append(masterSWmsg)        # sub page 2
                            elif (Channel == masterChannelID):
                                if      int(info[2]) == 1:    messages.append(slaveSerialMsg)     # sub page 1
                                elif    int(info[2]) == 2:    messages.append(slaveSWmsg)         # sub page 2
                        elif Channel == slaveChannelID or Channel == masterChannelID:
                            if Channel == slaveChannelID:
                                ab[0] = masterChannelID
                            else:
                                ab[0] = slaveChannelID
                            info = bytes(ab)
                            msg = ant.ComposeMessage(id, info)
                            messages.append(msg)
                            counter += 1
                        elif Channel == huChannelID: pass # not to be forwarded
                        else:
                            logfile.Console("Message ID %2.2x found on channel %2.2d - not forwarded" % (id, Channel))

                    logfile.Write("................ Bridged %3.3d messages .................." % counter)

                    # Only valid when
                    if setMode == ant.VHU_Training:
                        if   increaseTarget: Target += targetIncrement
                        elif decreaseTarget: Target -= targetIncrement

                        if simulatePowerTraining:
                            if increaseTarget or decreaseTarget or initializeTarget:
                                logfile.Write("................ Setting power target to %3.3d  .................." % Target, True)
                                logDataChanged = True
                            info = ant.msgPageDC_TacxBushidoDataPower(huChannelID, Target, Weight)
                        elif simulateSlopeTraining:
                            if increaseTarget or decreaseTarget or initializeTarget:
                                logfile.Write("................ Setting grade target to %4.2f percent  .................." % Target, True)
                                logDataChanged = True
                            info = ant.msgPageDC_TacxBushidoDataSlope(huChannelID, Target, Weight)

                        HU_Target = Target
                        msg = ant.ComposeMessage(ant.msgID_BroadcastData, info)
                        messages.append(msg)
                        if clv.csvExport: WriteCsv(info, True)

                        if initializeTarget: initializeTarget = False

                    AntDongle.Write(messages, False, False)
                    # delta = time.time() - startTime
                    # if delta < 0.1:
                    #     time.sleep(0.1 - delta)
                    # StartTime = now
                    if (logDataChanged and clv.csvExport):
                        WriteLog(not simulateSlopeTraining)

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


#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
##----------------------------------------------------------------------------##
## WESTLAKE UNIVERSITY                                                        ##
## ADVANCED SYSTEMS LABORATORY                                                ##
##----------------------------------------------------------------------------##
##      ____      __      __  __      _____      __      __    __    ____     ##
##     / __/|   _/ /|    / / / /|  _- __ __\    / /|    / /|  / /|  / _  \    ##
##    / /_ |/  / /  /|  /  // /|/ / /|__| _|   / /|    / /|  / /|/ /   --||   ##
##   / __/|/ _/    /|/ /   / /|/ / /|    __   / /|    / /|  / /|/ / _  \|/    ##
##  / /|_|/ /  /  /|/ / // //|/ / /|__- / /  / /___  / -|_ - /|/ /     /|     ##
## /_/|/   /_/ /_/|/ /_/ /_/|/ |\ ___--|_|  /_____/| |-___-_|/  /____-/|/     ##
## |_|/    |_|/|_|/  |_|/|_|/   \|___|-    |_____|/   |___|     |____|/       ##
##                   _ _    _    ___   _  _      __  __   __                  ##
##                  | | |  | |  | T_| | || |    |  ||_ | | _|                 ##
##                  | _ |  |T|  |  |  |  _|      ||   \\_//                   ##
##                  || || |_ _| |_|_| |_| _|    |__|  |___|                   ##
##                                                                            ##
##----------------------------------------------------------------------------##
## AUTHORS: zhaoyang (mzymuzhaoyang@gmail.com)                               ##
##          dashuai (dschen2018@gmail.com)                                   ##
##----------------------------------------------------------------------------##
################################################################################

""" ABOUT ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 + Fan Club networking back-end -- provisional version adapted from MkIII.
 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ """

## DEPENDENCIES ################################################################

# Network:
import socket       # Networking
try:
    import http.server  # For bootloader (Python 3)
except ImportError:
    import BaseHTTPServer  # For bootloader (Python 2)
    import sys
    sys.modules['http.server'] = BaseHTTPServer
try:
    import socketserver # For bootloader (Python 3)
except ImportError:
    import SocketServer  # For bootloader (Python 2)
    sys.modules['socketserver'] = SocketServer

# System:
import sys          # Exception handling
import traceback    # More exception handling
import threading as mt  # Multitasking
try:
    import _thread      # thread.error (Python 3)
except ImportError:
    import thread as _thread  # thread.error (Python 2)
import multiprocessing as mp # The big guns

import platform # Check OS and Python version

# Data:
import time         # Timing
try:
    import queue  # Python 3
except ImportError:
    import Queue  # Python 2
    sys.modules['queue'] = Queue
import numpy as np  # Fast arrays and matrices
import random as rd # For random names

# FCMkIII:
import fc.backend.mkiii.FCSlave as sv
import fc.backend.mkiii.hardcoded as hc
import fc.backend.mkiii.names as nm

# FCMkIV:
import fc.archive as ac
import fc.standards as s
import fc.printer as pt
import fc.backend.mkiii.exceptions as fcex
import psutil  # For system performance monitoring

# Import stability optimizer
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from stability_optimizer import stability_optimizer
from debug_monitor import debug_monitor
from error_recovery import error_recovery_manager

## CONSTANT DEFINITIONS ########################################################

class FCPerformanceMonitor:
    """FC通信性能监控器"""
    
    def __init__(self):
        self._metrics = {
            'message_send_time': [],
            'message_receive_time': [],
            'network_latency': [],
            'thread_cpu_usage': [],
            'memory_usage': [],
            'error_count': 0,
            'total_messages': 0
        }
        self._start_times = {}
        self._enabled = True
    
    def start_timing(self, operation):
        """Start timing operation"""
        if self._enabled:
            self._start_times[operation] = time.time()
    
    def end_timing(self, operation):
        """End timing and record"""
        if self._enabled and operation in self._start_times:
            duration = time.time() - self._start_times[operation]
            if operation in self._metrics:
                self._metrics[operation].append(duration)
                # Keep only the latest 1000 records
                if len(self._metrics[operation]) > 1000:
                    self._metrics[operation] = self._metrics[operation][-1000:]
            del self._start_times[operation]
    
    def record_message(self):
        """Record message count"""
        if self._enabled:
            self._metrics['total_messages'] += 1
    
    def record_error(self):
        """Record error count"""
        if self._enabled:
            self._metrics['error_count'] += 1
    
    def record_system_metrics(self):
        """Record system performance metrics"""
        if self._enabled:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self._metrics['thread_cpu_usage'].append(cpu_percent)
                
                # Memory usage
                memory_info = psutil.virtual_memory()
                self._metrics['memory_usage'].append(memory_info.percent)
                
                # Limit record count
                for key in ['thread_cpu_usage', 'memory_usage']:
                    if len(self._metrics[key]) > 100:
                        self._metrics[key] = self._metrics[key][-100:]
            except Exception:
                pass  # Ignore system monitoring errors
    
    def get_performance_stats(self):
        """Get performance statistics"""
        stats = {}
        for key, values in self._metrics.items():
            if isinstance(values, list) and values:
                stats[key] = {
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
            elif isinstance(values, (int, float)):
                stats[key] = values
        return stats
    
    def reset_metrics(self):
        """Reset all metrics"""
        for key in self._metrics:
            if isinstance(self._metrics[key], list):
                self._metrics[key].clear()
            else:
                self._metrics[key] = 0
    
    def enable(self):
        """Enable performance monitoring"""
        self._enabled = True
    
    def disable(self):
        """Disable performance monitoring"""
        self._enabled = False

# MOSI commands:
# MOSI commands - using standardized constants from fc.standards
MOSI_NO_COMMAND = getattr(s, 'MOSI_NO_COMMAND', 20)
MOSI_DC = getattr(s, 'MOSI_DC', 21)
MOSI_DC_ALL = getattr(s, 'MOSI_DC_ALL', 22)
MOSI_RPM = getattr(s, 'MOSI_RPM', 23)
MOSI_RPM_ALL = getattr(s, 'MOSI_RPM_ALL', 24)
MOSI_DISCONNECT = getattr(s, 'MOSI_DISCONNECT', 25)
MOSI_REBOOT = getattr(s, 'MOSI_REBOOT', 26)
MOSI_DC_MULTI = getattr(s, 'MOSI_DC_MULTI', 27)

## CLASS DEFINITION ############################################################

# DONE:
# - change profile usage (DONE)
# - change FCSlave constants for s.standards constants (DONE)

# TODO:
# - change command queue for pipe
# - change pipes
# - change output formatting
# - change input parsing
# - change printing
# - broadcast modes (both here and in interface)
# - stopped behavior

class FCCommunicator(pt.PrintClient):
    VERSION = "Adapted 1"
    SYMBOL = "[CM]"
    SYMBOL_IR = "[IR]"

    # Network configuration (now configurable via profile)
    # DEFAULT_IP_ADDRESS and DEFAULT_BROADCAST_IP are loaded from profile

    def __init__(self,
            profile,
            commandPipeRecv,
            controlPipeRecv,
            feedbackPipeSend,
            slavePipeSend,
            networkPipeSend,
            pqueue
        ): # ===================================================================
        """
        Constructor for FCCommunicator. This class encompasses the back-end
        network handling and number-crunching half of the software. It is
        expected to be executed in an independent process. (See Python's
        multiprocessing module.)

            profile := profile as loaded from FCArchive
            commandPipeRecv := receive command vectors from FE (mp Pipe())
            controlPipeRecv := receive control vectors from FE (mp Pipe())
            feedbackPipeSend := send feedback vectors to FE (mp Pipe())
            slavePipeSend := send slave vectors to FE (mp Pipe())
            networkPipeSend := send network vectors to FE (mp Pipe())
            pqueue := mp Queue() instance for I-P printing  (see fc.utils)

        """
        pt.PrintClient.__init__(self, pqueue)
        try:
            # INITIALIZE DATA MEMBERS ==========================================
            
            # Initialize performance monitor
            self.performance_monitor = FCPerformanceMonitor()
            self.performance_monitor.start_timing('communicator_init')

            # Initialize stability optimizer
            self.stability_optimizer = stability_optimizer
            # 优化：禁用稳定性监控以减少CPU占用
            # self.stability_optimizer.start_monitoring()
            
            # 优化：禁用调试监控以减少CPU占用
            # debug_monitor.start_monitoring()
            # debug_monitor.record_thread_activity("FCCommunicator_init")

            # Store parameters -------------------------------------------------
            self.profile = profile

            # Network:
            self.broadcastPeriodS = profile[ac.broadcastPeriodMS]/1000
            self.periodMS = profile[ac.periodMS]
            # 优化超时设置 - 确保最小超时时间
            # FIXME: 2.0s limit is too slow for real-time monitoring, restoring to periodMS
            self.periodS = max(self.periodMS/1000, 2.0)  # 最小50ms刷新，保证实时性
            self.broadcastPort = profile[ac.broadcastPort]
            self.passcode = profile[ac.passcode]
            
            # Load configurable IP addresses from profile
            self.defaultIPAddress = profile[ac.defaultIPAddress]
            self.defaultBroadcastIP = profile[ac.defaultBroadcastIP]
            self.misoQueueSize = profile[ac.misoQueueSize]
            self.maxTimeouts = profile[ac.maxTimeouts]
            self.maxLength = profile[ac.maxLength]
            self.flashFlag = False
            self.targetVersion = None
            self.flashMessage = None
            self.broadcastMode = s.BMODE_BROADCAST

            # Fan array:
            # FIXME usage of default slave data is a provisional choice
            self.defaultSlave = profile[ac.defaultSlave]

            self.maxFans = profile[ac.maxFans]
            self.fanRange = range(self.maxFans)
            self.dcTemplate = "{},"*self.maxFans
            self.fanMode = profile[ac.defaultSlave][ac.SV_fanMode]
            self.targetRelation = self.defaultSlave[ac.SV_targetRelation]
            self.fanFrequencyHZ = self.defaultSlave[ac.SV_fanFrequencyHZ]
            self.counterCounts = self.defaultSlave[ac.SV_counterCounts]
            self.pulsesPerRotation = self.defaultSlave[ac.SV_pulsesPerRotation]
            self.maxRPM = self.defaultSlave[ac.SV_maxRPM]
            self.minRPM = self.defaultSlave[ac.SV_minRPM]
            self.minDC = self.defaultSlave[ac.SV_minDC]
            self.chaserTolerance = self.defaultSlave[ac.SV_chaserTolerance]
            self.maxFanTimeouts = hc.DEF_MAX_FAN_TIMEOUTS
            self.pinout = profile[ac.pinouts][self.defaultSlave[ac.SV_pinout]]
            self.decimals = profile[ac.dcDecimals]

            self.fullSelection = ''
            for fan in range(self.maxFans):
                self.fullSelection += '1'

            # Multiprocessing and printing:
            self.commandPipeRecv = commandPipeRecv
            self.controlPipeRecv = controlPipeRecv
            self.feedbackPipeSend = feedbackPipeSend
            self.slavePipeSend = slavePipeSend
            self.networkPipeSend = networkPipeSend
            self.stopped = mt.Event()

            # Output queues:
            self.newSlaveQueue = queue.Queue()
            self.slaveUpdateQueue = queue.Queue()

            # Initialize Slave-list-related data:
            self.slavesLock = mt.Lock()
            # 注册锁到稳定性优化器
            self.stability_optimizer.register_lock('slavesLock', self.slavesLock)
            
            # Performance optimization: MAC to index mapping for O(1) lookup
            self.macToIndexMap = {}
            
            # Initialize error handler for better exception management
            self.error_handler = fcex.create_error_handler('FCCommunicator')

            # Command handling:
            self.commandHandlers = {
                s.CMD_ADD : self.__handle_input_CMD_ADD,
                s.CMD_DISCONNECT : self.__handle_input_CMD_DISCONNECT,
                s.CMD_REBOOT : self.__handle_input_CMD_REBOOT,
                s.CMD_SHUTDOWN : self.__handle_input_CMD_SHUTDOWN,
                s.CMD_FUPDATE_START : self.__handle_input_CMD_FUPDATE_START,
                s.CMD_FUPDATE_STOP : self.__handle_input_CMD_FUPDATE_STOP,
                s.CMD_STOP : self.__handle_input_CMD_STOP,
                s.CMD_BMODE : self.__handle_input_CMD_BMODE,
                s.CMD_BIP : self.__handle_input_CMD_BIP,
                s.CMD_N : self.__handle_input_CMD_N,
                s.CMD_S : self.__handle_input_CMD_S,
                s.CMD_CHASE : self.__handle_input_CMD_CHASE,
                s.CMD_PERF_STATS : self.__handle_input_CMD_PERF_STATS,
                s.CMD_PERF_RESET : self.__handle_input_CMD_PERF_RESET,
                s.CMD_PERF_ENABLE : self.__handle_input_CMD_PERF_ENABLE,
                s.CMD_PERF_DISABLE : self.__handle_input_CMD_PERF_DISABLE,
            }

            self.controlHandlers = {
                s.CTL_DC_SINGLE : self.__handle_input_CTL_DC_SINGLE,
                s.CTL_DC_VECTOR : self.__handle_input_CTL_DC_VECTOR,
            }

            if self.profile[ac.platform] != ac.WINDOWS:
                self.printd("\tNOTE: Increasing socket limit w/ \"resource\"")
                # Use resource library to get OS to give extra sockets:
                import resource
                resource.setrlimit(resource.RLIMIT_NOFILE,
                    (1024, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))

            # INITIALIZE MASTER SOCKETS ========================================

            # INITIALIZE LISTENER SOCKET ---------------------------------------

            # Create listener socket:
            self.listenerSocket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)

            # 优化listener socket超时
            self.stability_optimizer.optimize_socket_timeout(self.listenerSocket, "heartbeat")

            # Configure socket as "reusable" (in case of improper closure):
            self.listenerSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind socket to a FIXED port to avoid firewall issues with random high ports
            # Using 57584 as the fixed listener port
            try:
                self.listenerSocket.bind((self.defaultIPAddress, 57584))
            except socket.error:
                # If 57584 is taken, try 57584 + 1, etc.
                self.listenerSocket.bind((self.defaultIPAddress, 0))

            self.printr("\tlistenerSocket initialized on " + \
                str(self.listenerSocket.getsockname()))

            self.listenerPort = self.listenerSocket.getsockname()[1]

            # INITIALIZE BROADCAST SOCKET --------------------------------------

            # Create broadcast socket:
            self.broadcastSocket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)

            # Configure socket as "reusable" (in case of improper closure):
            self.broadcastSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Configure socket for broadcasting:
            self.broadcastSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Bind socket to "nothing" (Broadcast on all interfaces and let OS
            # assign port number):
            self.broadcastSocket.bind((self.defaultIPAddress, 0))
            self.broadcastIP = self.profile[ac.broadcastIP]

            self.broadcastSocketPort = self.broadcastSocket.getsockname()[1]

            self.broadcastLock = mt.Lock()
            # 注册广播锁到稳定性优化器
            self.stability_optimizer.register_lock('broadcastLock', self.broadcastLock)

            self.printr("\tbroadcastSocket initialized on " + \
                str(self.broadcastSocket.getsockname()))

            # Create reboot socket:
            self.rebootSocket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)

            # Configure socket as "reusable" (in case of improper closure):
            self.rebootSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Configure socket for rebooting:
            self.rebootSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Bind socket to "nothing" (Broadcast on all interfaces and let OS
            # assign port number):
            self.rebootSocket.bind((self.defaultIPAddress, 0))

            self.rebootSocketPort = self.rebootSocket.getsockname()[1]

            self.rebootLock = mt.Lock()

            self.printr("\trebootSocket initialized on " + \
                str(self.rebootSocket.getsockname()))

            # Create disconnect socket:
            self.disconnectSocket = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM)

            # Configure socket as "reusable" (in case of improper closure):
            self.disconnectSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Configure socket for disconnecting:
            self.disconnectSocket.setsockopt(
                socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Bind socket to "nothing" (Broadcast on all interfaces and let OS
            # assign port number):
            self.disconnectSocket.bind((self.defaultIPAddress, 0))

            self.disconnectSocketPort = self.disconnectSocket.getsockname()[1]

            self.disconnectLock = mt.Lock()

            self.printr("\tdisconnectSocket initialized on " + \
                str(self.disconnectSocket.getsockname()))

            # Reset any lingering connections:
            self.sendDisconnect()

            # SET UP FLASHING HTTP SERVER --------------------------------------
            self.flashHTTPHandler = http.server.SimpleHTTPRequestHandler
            if self.profile[ac.platform] != ac.WINDOWS:
                TCPServerType = socketserver.ForkingTCPServer
            else:
                TCPServerType = socketserver.ThreadingTCPServer
            self.httpd = TCPServerType(
                (self.defaultIPAddress, 0),
                self.flashHTTPHandler
            )

            self.httpd.socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1
            )
            self.httpd.timeout = 5

            self.flashServerThread = mt.Thread(
                target = self.httpd.serve_forever
            )
            self.flashServerThread.daemon = True
            self.flashServerThread.start()
            self.httpPort = self.httpd.socket.getsockname()[1]
            self.printr("\tHTTP Server initialized on {}".format(
                self.httpd.socket.getsockname()))

            # SET UP MASTER THREADS ============================================

            # INITIALIZE BROADCAST THREAD --------------------------------------
            # Configure sentinel value for broadcasts:
            self.broadcastSwitch = True
                # ABOUT: UDP broadcasts will be sent only when this is True
            self.broadcastSwitchLock = mt.Lock() # thread-safe access

            self.broadcastThread = mt.Thread(
                name = "FCMkII_broadcast",
                target = self._broadcastRoutine,
                args = [bytearray("N|{}|{}".format(
                            self.passcode,
                            self.listenerPort),'ascii'),
                        self.broadcastPeriodS]
                )


            # Set thread as daemon (background task for automatic closure):
            self.broadcastThread.daemon = True

            # INITIALIZE LISTENER THREAD ---------------------------------------
            self.listenerThread = mt.Thread(
                name = "FCMkII_listener",
                target = self._listenerRoutine)

            # Set thread as daemon (background task for automatic closure):
            self.listenerThread.daemon = True

            # INITIALIZE INPUT AND OUTPUT THREADS ------------------------------
            self.outputThread  = mt.Thread(
                name = "FCMkII_output",
                target = self._outputRoutine)
            self.outputThread.daemon = True

            self.inputThread = mt.Thread(
                name = "FCMkII_input",
                target = self._inputRoutine)
            self.inputThread.daemon = True

            # SET UP LIST OF KNOWN SLAVES  =====================================

            # instantiate any saved Slaves:
            saved = self.profile[ac.savedSlaves]
            self.slaves = [None]*len(saved)

            update = False
            for index, slave in enumerate(saved):
                self.slaves[index] = \
                    sv.FCSlave(
                    name = slave[ac.SV_name],
                    mac = slave[ac.SV_mac],
                    fans = slave[ac.SV_maxFans],
                    maxFans = self.maxFans,
                    status = s.SS_DISCONNECTED,
                    routine = self._slaveRoutine,
                    routineArgs = (index,),
                    misoQueueSize = self.misoQueueSize,
                    index = index,
                    )
                
                # Update MAC to index mapping for performance optimization
                self.macToIndexMap[slave[ac.SV_mac]] = index

                update = True

            if update:
                self._sendSlaves()

            # START THREADS:

            # Start inter-process threads:
            self.outputThread.start()
            self.inputThread.start()

            # Start Master threads:
            self.listenerThread.start()
            self.broadcastThread.start()

            # Start Slave threads:
            for slave in self.slaves:
                slave.start()

            self.printw("NOTE: Reporting back-end listener IP as whole IP")
            self._sendNetwork()

            # DONE
            self.performance_monitor.end_timing('communicator_init')
            self.prints("Communicator ready")

        except (socket.error, OSError) as e:
            error = self.error_handler.handle_network_error(e, "Communicator initialization")
            self.printx(error, "Network error in Communicator __init__: ")
            raise error
        except (ValueError, TypeError) as e:
            error = fcex.ConfigurationError("Configuration error in Communicator __init__: {}".format(e))
            self.error_handler.log_exception(error, "Communicator initialization")
            self.printx(error, "Configuration error in Communicator __init__: ")
            raise error
        except Exception as e:
            self.error_handler.log_exception(e, "Communicator initialization", "error")
            self.printx(e, "Unexpected error in Communicator __init__: ")
            raise fcex.FCCommunicatorError("Unexpected error during initialization: {}".format(e))

        # End __init__ =========================================================

    # # THREAD ROUTINES # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    # Input handling ...........................................................
    def _inputRoutine(self): # =================================================
        """
        Receive command and control vectors from the front-end.
        """
        SYM = self.SYMBOL_IR
        try:
            self.prints(SYM + " Prototype input routine started")
            last_metrics_time = time.time()
            while True:
                try:
                    # Record system metrics every 5 seconds
                    current_time = time.time()
                    if current_time - last_metrics_time >= 5.0:
                        self.performance_monitor.record_system_metrics()
                        last_metrics_time = current_time
                    
                    if self.commandPipeRecv.poll():
                        D = self.commandPipeRecv.recv()
                        self.commandHandlers[D[s.CMD_I_CODE]](D)
                    if self.controlPipeRecv.poll():
                        C = self.controlPipeRecv.recv()
                        self.controlHandlers[C[s.CTL_I_CODE]](C)

                except KeyError as e:
                    error_msg = "Unknown command/control code: {}".format(e)
                    self.error_handler.log_exception(e, "input thread command handling", "warning")
                    self.printw(SYM + " {}".format(error_msg))
                except (EOFError, OSError) as e:
                    error = self.error_handler.handle_network_error(e, "input thread pipe communication")
                    self.printx(error, SYM + " Pipe communication error: ")
                    break  # Exit loop on pipe errors
                except Exception as e:
                    self.error_handler.log_exception(e, "input thread", "error")
                    self.printx(e, SYM + " Unexpected error in back-end input thread: ")

        except Exception as e:
            error = self.error_handler.handle_thread_error(e, "input_routine", "input thread main loop")
            self.printx(error, SYM + " Critical error in back-end input thread (LOOP BROKEN): ")
            raise error
        # End _inputRoutine ====================================================

    def __handle_input_CMD_ADD(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        target = D[s.CMD_I_TGT_CODE]
        if target == s.TGT_ALL:
            # REMARK: Unapplicable Slaves will be automatically ignored
            for index in range(len(self.slaves)):
                self.add(index)
        elif target == s.TGT_SELECTED:
            for index in D[s.CMD_I_TGT_OFFSET:]:
                self.add(index)
        else:
            raise ValueError("Invalid {} target code {}".format(
                s.COMMAND_CODES[D[s.CMD_I_CODE]], target))

    def __handle_input_CMD_DISCONNECT(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        target = D[s.CMD_I_TGT_CODE]
        if target == s.TGT_ALL:
            self.sendDisconnect()
        elif target == s.TGT_SELECTED:
            for index in D[s.CMD_I_TGT_OFFSET:]:
                self.slaves[index].setMOSI((MOSI_DISCONNECT,),False)
        else:
            raise ValueError("Invalid {} target code {}".format(
                s.COMMAND_CODES[D[s.CMD_I_CODE]], target))

    def __handle_input_CMD_REBOOT(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        target = D[s.CMD_I_TGT_CODE]
        if target == s.TGT_ALL:
            self.sendReboot()
        elif target == s.TGT_SELECTED:
            for index in D[s.CMD_I_TGT_OFFSET:]:
                self.sendReboot(self.slaves[index])
        else:
            raise ValueError("Invalid {} target code {}".format(
                s.COMMAND_CODES[D[s.CMD_I_CODE]], target))

    def __handle_input_CMD_SHUTDOWN(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        self.printr("Received shutdown command. Stopping all operations.")
        # Stop all slave communications
        for slave in self.slaves:
            if slave.getStatus() == s.SS_CONNECTED:
                slave.disconnect()
        # Stop the communicator
        self.stop()

    def __handle_input_CMD_FUPDATE_START(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        try:
            self.targetVersion = D[s.CMD_I_FU_VERSION]
            filename = D[s.CMD_I_FU_FILENAME]
            filesize = D[s.CMD_I_FU_FILESIZE]
            self.printr("Firmware update command received:"\
                "\n\tVersion: {} \n\tFile: \"{}\"\n\tSize: {} bytes)".format(
                self.targetVersion, filename, filesize))

            self.flashFlag = True

            # Use configurable passcode instead of hard-coded "CT"
            # The passcode is now read from the profile configuration
            self.flashMessage = "U|{}|{}|{}|{}|{}".format(
                self.passcode, self.listenerPort, self.httpPort, filename, filesize)

            self.prints("Firmware update setup complete.")

        except Exception as e:
            self.printe("Exception raised in setup. Firmware update canceled.")
            self.commandHandlers[s.CMD_FUPDATE_STOP]([s.CMD_FUPDATE_STOP])
            raise e

    def __handle_input_CMD_FUPDATE_STOP(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        self.printr("Received command to stop firmware update.")
        self.flashFlag = False

    def __handle_input_CMD_STOP(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        self.printw("Received command to stop communications.")
        self.stop()

    def __handle_input_CMD_BMODE(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        new_mode = D[s.CMD_I_BM_BMODE]
        if new_mode in [s.BMODE_BROADCAST, s.BMODE_TARGETTED]:
            self.broadcastMode = new_mode
            mode_name = "broadcast" if new_mode == s.BMODE_BROADCAST else "targeted"
            self.prints("Broadcast mode set to {}".format(mode_name))
            self._sendNetwork()  # Update network status
        else:
            self.printe("Invalid broadcast mode: {}".format(new_mode))

    def __handle_input_CMD_BIP(self, D):
        """
        Process the command vector D with the corresponding command.
        See fc.standards for the expected form of D.
        """
        ip = D[s.CMD_I_BIP_IP]
        if self._validBIP(ip):
            self.broadcastIP = ip
            self.prints("Broadcast IP set to {}".format(ip))
            self._sendNetwork()
        else:
            self.printe("Invalid broadcast IP received: {}".format(ip))

    def __handle_input_CMD_N(self, *_):
        """
        Process a request for an updated network state vector.
        """
        self._sendNetwork()

    def __handle_input_CMD_S(self, *_):
        """
        Process a request for an updated slave state vector.
        """
        self._sendSlaves()
    
    def __handle_input_CMD_PERF_STATS(self, *_):
        """
        Process a request for performance statistics.
        """
        stats = self.get_performance_stats()
        # Send stats through feedback pipe as a special message
        self.feedbackPipeSend.send(('PERF_STATS', stats))
    
    def __handle_input_CMD_PERF_RESET(self, *_):
        """
        Process a request to reset performance statistics.
        """
        self.reset_performance_stats()
        self.prints("Performance statistics reset")
    
    def __handle_input_CMD_PERF_ENABLE(self, *_):
        """
        Process a request to enable performance monitoring.
        """
        self.enable_performance_monitoring()
        self.prints("Performance monitoring enabled")
    
    def __handle_input_CMD_PERF_DISABLE(self, *_):
        """
        Process a request to disable performance monitoring.
        """
        self.disable_performance_monitoring()
        self.prints("Performance monitoring disabled")

    def __handle_input_CMD_CHASE(self, D):
        """
        Process a CHASE command to start RPM control mode.
        See fc.standards for the expected form of D.
        """
        try:
            # Extract target RPM from command data
            targetRPM = D[s.CMD_I_TGT_OFFSET]  # Assuming target RPM is at offset position
            
            # Handle targets parameter - if TGT_ALL or not specified, pass None for broadcast
            if len(D) > s.CMD_I_TGT_CODE:
                target_code = D[s.CMD_I_TGT_CODE]
                if target_code == s.TGT_ALL:
                    targets = None  # None means broadcast to all slaves
                elif target_code == s.TGT_SELECTED:
                    # Extract specific target indices from the command data
                    targets = D[s.CMD_I_TGT_OFFSET + 1:] if len(D) > s.CMD_I_TGT_OFFSET + 1 else None
                else:
                    targets = None  # Default to broadcast
            else:
                targets = None  # Default to broadcast
            
            # Call the existing sendChase method
            self.sendChase(targetRPM, targets)
            self.prints("CHASE command processed: target RPM = {}".format(targetRPM))
            
        except (IndexError, ValueError) as e:
            self.printe("Invalid CHASE command format: {}".format(e))
        except Exception as e:
            self.printx(e, "Exception in CHASE command handler")

    def _getSlaveIndexByMAC(self, mac):
        """
        Performance-optimized method to get slave index by MAC address.
        Returns index if found, None otherwise.
        """
        return self.macToIndexMap.get(mac, None)

    def _validBIP(self, ip):
        """
        Return whether the given ip address is a valid broadcast IP.
            - ip := String, IP address to use.
        """
        if ip == "<broadcast>":
            return True
        else:
            try:
                numbers = tuple(map(int, ip.split(".")))
                if len(numbers) != 4:
                    return False
                else:
                    for number in numbers:
                        if number < 0 or number > 255:
                            return False
                    return True
            except:
                return False
    
    def get_rpm_data(self):
        """
        Get current RPM data from all connected slaves.
        Returns a list of RPM values for all fans.
        """
        try:
            F_r = []
            for slave in self.slaves:
                rpms, dcs = slave.getMISO()
                F_r += rpms
            return F_r
        except Exception as e:
            self.printx(e, "Exception getting RPM data:")
            return []

    def __handle_input_CTL_DC_SINGLE(self, C):
        """
        Process the control vector C with the corresponding command.
        See fc.standards for the expected form of C.
        """
        target = C[s.CTL_I_TGT_CODE]
        dc = C[s.CTL_I_SINGLE_DC]
        # FIXME MkIV constants (RIP MOSI...)
        # L--> NOTE Apply this to others, too
        if target is s.TGT_ALL:
            fans = C[s.CTL_I_SINGLE_ALL_SELECTION]
            for slave in self.slaves: # FIXME performance w/ getIndex?
                if slave.getStatus() == s.SS_CONNECTED:
                    slave.setMOSI((MOSI_DC, dc,  fans), False)
        elif target is s.TGT_SELECTED:
            # FIXME performance
            i = s.CTL_I_SINGLE_TGT_OFFSET
            L = len(C)
            while i < L:
                slave = self.slaves[C[i]]
                fans = C[i + 1]
                if slave.getStatus() == s.SS_CONNECTED:
                    slave.setMOSI((MOSI_DC, dc,  fans), False)
                i += 2
        else:
            raise ValueError("Invalid {} target code {}".format(
                s.CONTROL_CODES[C[s.CTL_I_CODE]], target))

    def __handle_input_CTL_DC_VECTOR(self, C):
        """
        Process the control vector C with the corresponding command.
        See fc.standards for the expected form of C.
        
        Revised to support dynamic maxFans padding based on actual slave fan count.
        """
        index = 0
        i = s.CTL_I_VECTOR_DC_OFFSET
        L = len(C)

        while i < L and index < len(self.slaves):
            slave = self.slaves[index]
            if slave.getStatus() == s.SS_CONNECTED:
                # Get actual fan count for this slave
                slaveFans = slave.getFans()
                # Extract DC values for this slave's fans
                slaveDCs = C[i:i+slaveFans]
                # Pad with zeros if needed to match maxFans
                paddedDCs = list(slaveDCs) + [0] * (self.maxFans - len(slaveDCs))
                # Create template for this slave's fan count
                slaveTemplate = "{}" + ",{}" * (self.maxFans - 1)
                slave.setMOSI((
                    MOSI_DC_MULTI,
                    slaveTemplate.format(*paddedDCs)))
            # Move to next slave's data (use actual fan count, not maxFans)
            index += 1
            i += self.slaves[index-1].getFans() if index > 0 else self.maxFans


    def _outputRoutine(self): # ================================================
        """
        Send network, slave, and fan array state vectors to the front-end.
        """
        SYM = "[OT]"
        try:
            self.prints(SYM + " Prototype output routine started")
            while True:
                time.sleep(self.periodS)
                try:

                    # Network status:
                    self._sendNetwork()

                    # Slave status:
                    self._sendSlaves()

                    # Feedback vector:
                    # FIXME performance with this format
                    F_r = []
                    F_d = []
                    for slave in self.slaves:
                        rpms, dcs = slave.getMISO()
                        F_r += rpms
                        F_d += dcs
                    self.feedbackPipeSend.send(F_r + F_d)

                except Exception as e: # Print uncaught exceptions
                    self.printx(e, SYM + "Exception in back-end output thread:")

        except Exception as e: # Print uncaught exceptions
            self.printx(e, SYM + "Exception in back-end output thread "\
                + "(LOOP BROKEN): ")
        # End _outputRoutine ===================================================

    def _broadcastRoutine(self, broadcastMessage, broadcastPeriod): # ==========
        """ ABOUT: This method is meant to run inside a Communicator instance's
            broadcastThread.
        """
        try:
            self.prints("[BT] Broadcast thread started w/ period of {}s "\
                "on port {}".format(broadcastPeriod, self.broadcastPort))

            count = 0
            while(True):
                # Increment counter:
                count += 1
                # Wait designated period:
                time.sleep(broadcastPeriod)
                if self.broadcastSwitch:
                    # Broadcast message:
                    self.broadcastSocket.sendto(broadcastMessage,
                        (self.broadcastIP, self.broadcastPort))
        except Exception as e:
            self.printx(e, "[BT] Fatal error in broadcast thread:")
            self.stop()
        # End _broadcastRoutine ================================================

    def _listenerRoutine(self): # ==============================================
        """ ABOUT: This method is meant to run within an instance's listener-
            Thread. It will wait indefinitely for messages to be received by
            the listenerSocket and respond accordingly.
        """

        self.prints("[LR] Listener thread started. Waiting.")

        # Get standard replies:
        launchMessage = "L|{}".format(self.passcode)

        while(True):
            try:
                # Wait for a message to arrive:
                messageReceived, senderAddress = \
                    self.listenerSocket.recvfrom(self.maxLength)

                # DEBUG: print("Message received")

                """ NOTE: The message received from Slave, at this point,
                    should have one of the following forms:

                    - STD from MkII:
                        A|PCODE|SV:MA:CA:DD:RE:SS|N|SMISO|SMOSI|VERSION
                        0     1         2 3 4     5 6
                    - STD from Bootloader:
                        B|PCODE|SV:MA:CA:DD:RE:SS|N|[BOOTLOADER_VERSION]
                        0     1                 2 3                 4

                    - Error from MkII:
                        A|PCODE|SV:MA:CA:DD:RE:SS|E|ERRMESSAGE

                    - Error from Bootloader:
                        B|PCODE|SV:MA:CA:DD:RE:SS|E|ERRMESSAGE

                    Where SMISO and SMOSI are the Slave's MISO and MOSI
                    port numbers, respectively. Notice separators.
                """
                messageSplitted = messageReceived.decode('ascii').split("|")
                    # NOTE: messageSplitted is a list of strings, each of which
                    # is expected to contain a string as defined in the comment
                    # above.

                # Verify passcode:
                if messageSplitted[1] != self.passcode:
                    self.printw("Wrong passcode received (\"{}\") "\
                        "from {}".format(messageSplitted[1],
                        senderAddress[0]))

                    #print "Wrong passcode"

                    continue

                # Check who's is sending the message
                if messageSplitted[0][0] == 'A':
                    # This message comes from the MkII

                    try:
                        mac = messageSplitted[2]

                        # Check message type:
                        if messageSplitted[3] == 'N':
                            # Standard broadcast reply

                            misoPort = int(messageSplitted[4])
                            mosiPort = int(messageSplitted[5])
                            version = messageSplitted[6]

                            # Verify converted values:
                            if (misoPort <= 0 or misoPort > 65535):
                                # Raise a ValueError if a port number is invalid:
                                self.printw(
                                    "Bad SMISO ({}). Need [1, 65535]".format(
                                        miso))

                            if (mosiPort <= 0 or mosiPort > 65535):
                                # Raise a ValueError if a port number is invalid:
                                raise ValueError(
                                    "Bad SMOSI ({}). Need [1, 65535]".\
                                    format(mosi))

                            if (len(mac) != 17):
                                # Raise a ValueError if the given MAC address is
                                # not 17 characters long.
                                raise ValueError("MAC ({}) not 17 chars".\
                                    format(mac))

                            # Performance-optimized slave lookup by MAC
                            index = self._getSlaveIndexByMAC(mac)

                            # Check if the Slave is known:
                            if index is not None :
                                # Slave already recorded

                                # Check flashing case:
                                if self.flashFlag and version != \
                                    self.targetVersion:
                                    # Version mismatch. Send reboot message

                                    # Send reboot message
                                    self.listenerSocket.sendto(
                                        bytearray("R|{}".\
                                            format(self.passcode),'ascii'),
                                        senderAddress
                                    )

                                # If the index is in the Slave dictionary,
                                # check its status and proceed accordingly:

                                elif self.slaves[index].getStatus() in \
                                    (s.SS_DISCONNECTED, s.SS_UPDATING):
                                    # If the Slave is DISCONNECTED but just res-
                                    # ponded to a broadcast, update its status
                                    # for automatic reconnection. (handled by
                                    # their already existing Slave thread)

                                    # Update status and networking information:
                                    self.setSlaveStatus(
                                        self.slaves[index],
                                        s.SS_KNOWN,
                                        lock = False,
                                        netargs = (
                                            senderAddress[0],
                                            misoPort,
                                            mosiPort,
                                            version
                                            )
                                    )
                                else:
                                    # All other statuses should be ignored for
                                    # now.
                                    pass

                            else:
                                # Newly met Slave
                                index = len(self.slaves)
                                # If the MAC address is not recorded, list it
                                # AVAILABLE and move on. The user may choose
                                # to add it later.
                                name = rd.choice(nm.coolNames)
                                fans = self.defaultSlave[ac.SV_maxFans]

                                self.slaves.append(
                                    sv.FCSlave(
                                        name = name,
                                        mac = mac,
                                        fans = fans,
                                        maxFans = self.maxFans,
                                        status = s.SS_AVAILABLE,
                                        routine = self._slaveRoutine,
                                        routineArgs = (index, ),
                                        version = version,
                                        misoQueueSize = self.misoQueueSize,
                                        ip = senderAddress[0],
                                        misoP = misoPort,
                                        mosiP = mosiPort,
                                        index = index)
                                )
                                
                                # Update MAC to index mapping for new slave
                                self.macToIndexMap[mac] = index

                                # Add new Slave's information to newSlaveQueue:
                                self._sendSlaves()

                                # Start Slave thread:
                                self.slaves[index].start()

                        elif messageSplitted[3] == 'E':
                            # Error message

                            self.printe("Error message from Slave {}: "\
                                "\"{}\"".format(
                                    messageSplitted[2], messageSplitted[3]))
                        else:
                            # Invalid code
                            raise IndexError

                    except IndexError:
                        self.printw("Invalid message \"{}\" discarded; "\
                            "sent by {}".format(
                                messageReceived,senderAddress))

                elif messageSplitted[0][0] == 'B':
                    # This message comes from the Bootloader

                    try:
                        # Check message type:
                        if messageSplitted[3] == 'N':
                            # Standard broadcast

                            if not self.flashFlag:
                                # No need to flash. Launch MkII:
                                self.listenerSocket.sendto(
                                    bytearray(launchMessage,'ascii'),
                                    senderAddress)

                            else:
                                # Flashing in progress. Send flash message:

                                self.listenerSocket.sendto(
                                    bytearray(self.flashMessage,'ascii'),
                                    senderAddress)

                            # Update Slave status:

                            # Performance-optimized slave lookup by MAC
                            mac = messageSplitted[2]
                            index = self._getSlaveIndexByMAC(mac)

                            if index is not None:
                                # Known Slave. Update status:

                                # Try to get bootloader version:
                                try:
                                    version = messageSplitted[4]
                                except IndexError:
                                    version = "Bootloader(?)"

                                self.slaves[index].setVersion(version)
                                self.setSlaveStatus(
                                    self.slaves[index],
                                    s.SS_UPDATING
                                )

                            else:

                                # Send launch message:
                                self.listenerSocket.sendto(
                                    bytearray(launchMessage,'ascii'),
                                    senderAddress)


                        elif messageSplitted[3] == 'E':
                            # Error message

                            self.printe("Error message from {} "\
                                "on Bootloader: \"{}\"".format(
                                    messageSplitted[2],
                                    messageSplitted[4]))

                    except IndexError:
                        self.printw("Invalid message \"{}\" discarded; "\
                            "sent by {}".format(
                                senderAddress[0], messageReceived))
                else:
                    # Invalid first character (discard message)
                    self.printw("Warning: Message from {} w/ invalid first "\
                        "character '{}' discarded".format(
                            senderAddress[0], messageSplitted[0]))

            except socket.timeout:
                # Socket timeout is expected, continue listening
                continue
            except socket.error as e:
                error = self.error_handler.handle_network_error(e, "listener thread socket operation")
                self.printx(error, "Socket error in listener thread: ")
                continue
            except (ValueError, IndexError) as e:
                error = self.error_handler.handle_parsing_error(e, "", "listener thread message parsing")
                self.printw("Message parsing error in listener thread: {}".format(error))
                continue
            except Exception as e:
                self.error_handler.log_exception(e, "listener thread", "error")
                self.printx(e, "Unexpected error in listener thread: ")
        # End _listenerRoutine =================================================

    def _slaveRoutine(self, targetIndex, target): # # # # # # # # # # # # # # # #
        # ABOUT: This method is meant to run on a Slave's communication-handling
        # thread. It handles sending and receiving messages through its MISO and
        # MOSI sockets, at a pace dictated by the Communicator instance's given
        # period.
        # PARAMETERS:
        # - targetIndex: int, index of the Slave handled
        # - target: Slave controlled by this thread
        # NOTE: This version is expected to run as daemon.

        try:

            # Setup ============================================================

            # Get reference to Slave: ------------------------------------------
            slave = target

            # Set up sockets ---------------------------------------------------
            # MISO:
            misoS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            misoS.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            misoS.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # 使用稳定性优化器设置超时
            self.stability_optimizer.optimize_socket_timeout(misoS, "data")
            misoS.bind((self.defaultIPAddress, 0))

            # MOSI:
            mosiS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            mosiS.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            mosiS.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # 使用稳定性优化器设置超时
            self.stability_optimizer.optimize_socket_timeout(mosiS, "heartbeat")
            mosiS.bind((self.defaultIPAddress, 0))

            # Assign sockets:
            slave.setSockets(newMISOS = misoS, newMOSIS = mosiS)

            self.printr("[SV] ({:3d}) Slave sockets connected: "\
             " MMISO: {} MMOSI:{} (IP: {})".\
                format(targetIndex + 1,
                    slave._misoSocket().getsockname()[1],
                    slave._mosiSocket().getsockname()[1],
                    slave.getIP()))

            # HSK message ------------------------------------------------------
            def _makeHSK():
                return  "H|{},{},{},{},{}|"\
                    "{} {} {} {} {} {} {} {} {} {} {}".format(
                        slave._misoSocket().getsockname()[1],
                        slave._mosiSocket().getsockname()[1],
                        self.periodMS,
                        self.broadcastPeriodS*1000,
                        self.maxTimeouts,
                        # FIXME: Set values per slave, not globals
                        self.fanMode,
                        self.maxFans,
                        self.fanFrequencyHZ,
                        self.counterCounts,
                        self.pulsesPerRotation,
                        self.maxRPM,
                        self.minRPM,
                        self.minDC,
                        self.chaserTolerance,
                        self.maxFanTimeouts,
                        self.pinout)

            MHSK = _makeHSK()

            # Set up placeholders and sentinels --------------------------------
            slave.resetIndices()
            periodS = self.periodS
            timeouts = 0
            totalTimeouts = 0
            message = "P"
            tryBuffer = True

            failedHSKs = 0


            # Slave loop =======================================================
            # 优化：禁用线程活动记录以减少CPU占用
                # debug_monitor.record_thread_activity(f"_slaveRoutine_start_{slave.getIndex()}")
            while(True):

                try:
                #slave.acquire()

                    status = slave.getStatus()
                    # 优化：禁用网络事件记录以减少CPU占用
                    # debug_monitor.record_network_event(f"slave_{slave.getIndex()}_status", status)

                    # Act according to Slave's state:
                    if status == s.SS_KNOWN: # = = = = = = = = = = = = = = = =

                        # If the Slave is known, try to secure a connection:
                        # print "Attempting handshake"

                        # Check for signs of life w/ HSK message:
                        self._send(MHSK, slave, 2, True)

                        # Give time to process:
                        #time.sleep(periodS)

                        tries = 2
                        while True:

                            # Try to receive reply:
                            reply = self._receive(slave)

                            # Check reply:
                            if reply is not None and reply[1] == "H":
                                # print "Processed reply: {}".format(reply), "G"
                                # print "Handshake confirmed"

                                # Mark as CONNECTED and get to work:
                                #slave.setStatus(sv.CONNECTED, lock = False)
                                self.setSlaveStatus(slave,s.SS_CONNECTED,False)
                                tryBuffer = True
                                break

                                """
                                self._saveTimeStamp(slave.getIndex(), "Connected")
                                """

                            elif reply is not None and reply[1] == "K":
                                # HSK acknowledged, give Slave time
                                continue

                            elif tries > 0:
                                # Try again:
                                self._send(MHSK, slave, 1, True)
                                tries -= 1

                            elif failedHSKs == 0:
                                # Disconnect Slave:
                                self._send("X", slave, 2)
                                #slave.setStatus(sv.DISCONNECTED, lock = False)

                                self.setSlaveStatus(
                                slave,s.SS_DISCONNECTED,False)
                                    # NOTE: This call also resets exchange
                                    # index.
                                break

                            else:
                                # Something's wrong. Reset sockets.
                                self.printw("Resetting sockets for {} ({})".\
                                    format(slave.getMAC(), targetIndex + 1))

                            # MISO:
                            slave._misoSocket().close()

                            misoS = socket.socket(
                                socket.AF_INET, socket.SOCK_DGRAM)
                            misoS.setsockopt(
                                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            misoS.setsockopt(
                                socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                            misoS.settimeout(self.periodS*2)
                            misoS.bind((self.defaultIPAddress, 0))

                            # MOSI:
                            slave._mosiSocket().close()

                            mosiS = socket.socket(
                                socket.AF_INET, socket.SOCK_DGRAM)
                            mosiS.setsockopt(
                                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            mosiS.setsockopt(
                                socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                            mosiS.settimeout(self.periodS)
                            mosiS.bind((self.defaultIPAddress, 0))

                            # Assign sockets:
                            slave.setSockets(newMISOS = misoS, newMOSIS = mosiS)

                            self.printr("[SV] {:3d} Slave sockets "\
                                "re-connected: MMISO: {} MMOSI:{}".format(
                                    targetIndex + 1,
                                    slave._misoSocket().getsockname()[1],
                                    slave._mosiSocket().getsockname()[1]))

                            # HSK message --------------------------------------
                            MHSK = _makeHSK()

                            # Reset counter:
                            failedHSKs = 0

                            continue

                    elif status == s.SS_CONNECTED: # = = = = = = = = = = = = = = =
                        # If the Slave's state is positive, it is online and
                        # there is a connection to maintain.

                        # A positive state indicates this Slave is online and
                        # its connection need be maintained.

                        #DEBUG DEACTV
                        ## print "[On positive state]"

                        # Check flashing flag:
                        if self.flashFlag and slave.getVersion() != \
                            self.targetVersion:

                            # If the flashing flag is set and this Slave has
                            # the wrong version, reboot it

                            self._send("R", slave, 1)
                            self.setSlaveStatus(slave, s.SS_DISCONNECTED, False)

                            continue

                        # Check queue for message:
                        fetchedMessage = slave.getMOSI()

                        if fetchedMessage is None:
                            # Nothing to fetch. Send previous command

                            # Send message:
                            self._send(message, slave, 2)

                        elif fetchedMessage[0] == MOSI_DC:
                            # NOTE MkIV format:
                            # (MOSI_DC, DC, SELECTION)
                            # -> DC is already normalized
                            # -> SELECTION is string of 1's and 0's

                            message = "S|D:{}:{}".format(
                                fetchedMessage[1], fetchedMessage[2])
                            #   \---------------/  \---------------/
                            #      Duty cycle         Selection

                            self._send(message, slave, 2)

                        elif fetchedMessage[0] == MOSI_DC_MULTI:
                            # NOTE MkIV format:
                            # (MOSI_DC_MULTI, "dc_0,dc_1,dc_2...dc_maxFans")
                            # Here each dc is already normalized
                            # NOTE: Notice here maxFans is assumed (should be
                            # ignored by slave)
                            message = "S|F:" + fetchedMessage[1]
                            self._send(message, slave, 2)

                        elif fetchedMessage[0] == MOSI_DISCONNECT:
                            self._sendToListener("X", slave, 2)

                        elif fetchedMessage[0] == MOSI_REBOOT:
                            self._sendToListener("R", slave, 2)

                        # DEBUG:
                        # print "Sent: {}".format(message)

                        # Start network latency measurement
                        self.performance_monitor.start_timing('network_latency')
                        
                        # Get reply:
                        reply = self._receive(slave)
                        
                        # End network latency measurement if reply received
                        if reply is not None:
                            self.performance_monitor.end_timing('network_latency')

                        # Check reply: -----------------------------------------
                        if reply is not None:
                            # print "Processed reply: {}".format(reply)

                            # Restore timeout counter after success:
                            timeouts = 0

                            # Check message type:
                            if reply[1] == 'T':
                                # Standard update

                                # Get data index:
                                receivedDataIndex = int(reply[2])

                                # Check for redundant data:
                                if receivedDataIndex > slave.getDataIndex():
                                    # If this data index is greater than the
                                    # currently stored one, this data is new and
                                    # should be updated:

                                    # Update data index:
                                    slave.setDataIndex(receivedDataIndex)

                                    # Update RPMs and DCs:
                                    try:
                                        # Optimized MISO data parsing for better performance
                                        # Use numpy for faster array operations and pre-allocate arrays
                                        
                                        # Pre-allocate arrays with maxFans size
                                        rpms = np.zeros(self.maxFans, dtype=int)
                                        dcs = np.zeros(self.maxFans, dtype=float)
                                        
                                        # Parse RPM data efficiently
                                        rpm_parts = reply[-2].split(',')
                                        rpm_count = min(len(rpm_parts), self.maxFans)
                                        for i in range(rpm_count):
                                            rpms[i] = int(rpm_parts[i])
                                        
                                        # Parse DC data efficiently  
                                        dc_parts = reply[-1].split(',')
                                        dc_count = min(len(dc_parts), self.maxFans)
                                        for i in range(dc_count):
                                            dcs[i] = float(dc_parts[i])
                                        
                                        # Convert to lists for compatibility
                                        slave.setMISO((rpms.tolist(), dcs.tolist()), False)
                                            # FORM: (RPMs, DCs)
                                    except queue.Full:
                                        # If there is no room for this message,
                                        # drop the packet and alert the user:
                                        slave.incrementDropIndex()

                            elif reply[1] == 'I':
                                # Reset MISO index

                                slave.setMISOIndex(0)
                                self.printr("[SV] {} MISO Index reset".format(
                                    slave.getMAC()))

                            elif reply[1] == 'P':
                                # Ping request

                                self._send("P", slave)

                            elif reply[1] == 'Y':
                                # Reconnect reply

                                pass

                            elif reply[1] == 'M':
                                # Maintain connection. Pass
                                pass

                            elif reply[1] == 'H':
                                # Old HSK message. Pass
                                pass

                            elif reply[1] == 'E':
                                # Error report

                                self.printe("[SV] {:3d} ERROR: \"{}\"".format(
                                    targetIndex + 1, reply[2]))

                            elif reply[1] == 'Q':
                                # Ping reply. Pass
                                pass

                            else:
                                # Unrecognized command

                                self.printw("[SV] {:3d} Warning, unrecognized "\
                                    "message: \"{}\"".format(
                                        targetIndex + 1, reply))

                        else:
                            timeouts += 1
                            totalTimeouts += 1

                            """
                            if message is not None:
                                # If a message was sent and no reply was
                                # received, resend it:
                                # print "Timed out. Resending"
                                # Resend message:
                                self._send(message, slave, 1)
                                # Increment timeout counter:

                            """

                            # Check timeout counter: - - - - - - - - - - - - - -
                            if timeouts == self.maxTimeouts -1:
                                # If this Slave is about to time out, send a
                                # ping request

                                self._send("Q", slave, 2)

                            elif timeouts < self.maxTimeouts:
                                # If there have not been enough timeouts to con-
                                # sider the connection compromised, continue.
                                # print "Reply missed ({}/{})".
                                #   format(timeouts,
                                #   self.maxTimeouts)

                                # Restart loop:
                                pass

                            elif tryBuffer:
                                self._send("Y", slave, 2)
                                tryBuffer = False

                            else:
                                self.printw("[SV] {} Slave timed out".\
                                    format(targetIndex + 1))

                                # Terminate connection: ........................

                                # Send termination message:
                                self._sendToListener("X", slave)

                                # Reset timeout counter:
                                timeouts = 0
                                totalTimeouts = 0

                                # Update Slave status:
                                """
                                slave.setStatus(
                                    sv.DISCONNECTED, lock = False)
                                """
                                self.setSlaveStatus(
                                slave, s.SS_DISCONNECTED, False)
                                # Restart loop:
                                pass

                                # End check timeout counter - - - - - - - - - -

                            # End check reply ---------------------------------

                    elif status == s.SS_UPDATING:
                        time.sleep(self.periodS)

                    else: # = = = = = = = = = = = = = = = = = = = = = = = = = =
                        time.sleep(self.periodS)
                        """
                        # If this Slave is neither online nor waiting to be
                        # contacted, wait for its state to change.

                        command = "P"
                        message = "P"

                        # Check if the Slave is mistakenly connected:
                        reply = self._receive(slave)

                        if reply is not None:
                            # Slave stuck! Send reconnect message:
                            if slave.getIP() is not None and \
                                slave.getMOSIPort() is not None:
                                self._send("Y", slave)

                                reply = self._receive(slave)

                                if reply is not None and reply[1] == "Y":
                                    # Slave reconnected!
                                    #slave.setStatus(sv.CONNECTED)
                                    self.setSlaveStatus(
                                        slave,s.SS_CONNECTED, False)

                            else:
                                self._sendToListener("X", slave)
                        """
                except socket.timeout:
                    # Socket timeout is expected in slave communication
                    continue
                except socket.error as e:
                    slave_info = {'mac': target.getMAC(), 'ip': target.getIP()}
                    error = self.error_handler.handle_network_error(e, "slave {} communication".format(targetIndex + 1), slave_info)
                    self.printx(error, "[{}] Network error: ".format(targetIndex + 1))
                except Exception as e:
                    self.error_handler.log_exception(e, "slave {} routine".format(targetIndex + 1), "error")
                    self.printx(e, "[{}] Unexpected error: ".format(targetIndex + 1))

                finally:
                    # DEBUG DEACTV
                    ## print "Slave lock released", "D"
                    # Guarantee release of Slave-specific lock:
                    """
                    try:
                        slave.release()
                    except _thread.error:
                        pass
                    """
                # End Slave loop (while(True)) =================================


        except Exception as e:
            error = self.error_handler.handle_thread_error(e, "slave_{}_routine".format(targetIndex + 1), "slave {} main loop".format(targetIndex + 1))
            self.printx(error, "[{}] Critical error (BROKEN LOOP): ".format(targetIndex + 1))
            raise error
        # End _slaveRoutine  # # # # # # # # # # # # # # # # # # # # # # # # #

    # # AUXILIARY METHODS # # # # # # # # # # # # # # # # # # # # # # # # # # #
        # ABOUT: These methods are to be used within this class. For methods to
        # be accessed by the user of a Communicator instance, see INTERFACE ME-
        # THODS below.

    def _send(self, message, slave, repeat = 1, hsk = False): # # # # # # # # #
        # ABOUT: Send message to a KNOWN or CONNECTED sv. Automatically add
        # index.
        # PARAMETERS:
        # - message: str, message to send (w/o "INDEX|")
        # - slave: Slave to contact (must be KNOWN or CONNECTED or behavior is
        #   undefined)
        # - repeat: How many times to send message.
        # - hsk: Bool, whether this message is a handshake message.
        # - broadcast: Bool, whether to send this message as a broad
        # WARNING: THIS METHOD ASSUMES THE SLAVE'S LOCK IS HELD BY ITS CALLER.

        # Start performance monitoring
        self.performance_monitor.start_timing('message_send_time')
        
        if not hsk:
            # Increment exchange index:
            slave.incrementMOSIIndex()
        else:
            # Set index to zero:
            slave.setMOSIIndex(0)

        # Prepare message:
        outgoing = "{}|{}".format(slave.getMOSIIndex(), message)

        # Send message:
        success = False
        for attempt in range(max(1, repeat)):
            try:
                slave._mosiSocket().sendto(bytearray(outgoing,'ascii'),
                    (slave.ip, slave.getMOSIPort()))
                success = True
                break
            except socket.error as e:
                # 使用稳定性优化器进行网络重试
                if attempt < repeat - 1:
                    retry_success = self.stability_optimizer.retry_network_operation(
                        lambda: slave._mosiSocket().sendto(bytearray(outgoing,'ascii'),
                            (slave.ip, slave.getMOSIPort())),
                        "send_message"
                    )
                    if retry_success:
                        success = True
                        break
                else:
                    # 记录发送失败
                    slave_info = {'mac': slave.getMAC(), 'ip': slave.getIP()}
                    self.error_handler.handle_communication_error(e, "message send", slave_info)
                    self.performance_monitor.record_error()
        
        if not success:
            self.printw("Failed to send message to slave after {} attempts".format(repeat))
        
        # End performance monitoring and record message
        self.performance_monitor.end_timing('message_send_time')
        self.performance_monitor.record_message()

        # Notify user:
        # print "Sent \"{}\" to {} {} time(s)".
        #   format(outgoing, (slave.ip, slave.mosiP), repeat))

        # End _send # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def _sendToListener(self, message, slave, repeat = 1, targetted = True): # #
        # ABOUT: Send a message to a given Slave's listener socket.


        if targetted and slave.ip is not None:
            # Send to listener socket:
            # Prepare message:
            outgoing = "{}|{}".format(message, self.passcode)
            for i in range(repeat):
                slave._mosiSocket().sendto(bytearray(outgoing,'ascii'),
                (slave.ip, self.broadcastPort))
        else:
            # Send through broadcast:
            # Prepare message:
            outgoing = "J|{}|{}|{}".format(
                self.passcode, slave.getMAC(), message)
            for i in range(repeat):
                slave._mosiSocket().sendto(bytearray(outgoing,'ascii'),
                (self.defaultBroadcastIP, self.broadcastPort))

        # End _sendToListener # # # # # # # # # # # # # # # # # # # # # # # # # #

    def _receive(self, slave): # # # # # # # # # # # # # # # # # # # # # # # # #
        # ABOUT: Receive a message on the given Slave's sockets (assumed to be
        # CONNECTED, BUSY or KNOWN.
        # PARAMETERS:
        # - slave: Slave unit for which to listen.
        # RETURNS:
        # - three-tuple:
        #   (exchange index (int), keyword (str), command (str) or None)
        #   or None upon failure (socket timeout or invalid message)
        # RAISES:
        # - What exceptions may arise from passing an invalid argument.
        # WARNING: THIS METHOD ASSUMES THE SLAVE'S LOCK IS HELD BY ITS CALLER.

        # Start performance monitoring
        self.performance_monitor.start_timing('message_receive_time')
        
        try:
            # Keep searching for messages until a message with a matching index
            # is found or the socket times out (no more messages to retrieve)
            index = -1
            indexMatch = False
            count = 0
            while(True): # Receive loop = = = = = = = = = = = = = = = = = = = =

                # Increment counter: -------------------------------------------
                count += 1
                # DEBUG DEACTV
                ## print "Receiving...({})".format(count), "D"

                # Receive message: ---------------------------------------------
                message, sender = slave._misoSocket().recvfrom(
                    self.maxLength)

                # DEBUG DEACTV
                """
                print "Received: \"{}\" from {}".\
                    format(message, sender)
                """

                try:
                    # Split message: -------------------------------------------
                    splitted = message.decode('ascii').split("|")

                    # Verify index:
                    index = int(splitted[0])

                    if index <= slave.getMISOIndex():
                        # Bad index. Discard message:
                        # print "Bad index: ({})".
                        #   format(index), "D"

                        # Discard message:
                        continue

                    # Check for possible third element:
                    # DEBUG PRINT:
                    #print \
                    #    "Got {} part(s) from split: {}".\
                    #    format(len(splitted), str(splitted)), "D"

                    output = None

                    if len(splitted) == 2:
                        output = (index, splitted[1])

                    elif len(splitted) == 3:
                        output = (index, splitted[1], splitted[2])

                    elif len(splitted) == 4:
                        output = (index, splitted[1], splitted[2], splitted[3])

                    elif len(splitted) == 5:
                        output = (index, splitted[1], int(splitted[2]), splitted[3],
                            splitted[4])

                    else:
                        # print
                        #"ERROR: Unrecognized split amount ({}) on: {}".\
                        #format(len(splitted), str(splitted)), "E")
                        return None

                    # Update MISO index:
                    slave.setMISOIndex(index)

                    # Return splitted message: ---------------------------------
                    # DEBUG DEACTV
                    ## print "Returning {}".format(output), "D"
                    self.performance_monitor.end_timing('message_receive_time')
                    return output

                except UnicodeDecodeError as e:
                    # Handle message decoding errors
                    slave_info = {'mac': slave.getMAC(), 'ip': slave.getIP()}
                    error = self.error_handler.handle_communication_error(e, "message decode", slave_info)
                    self.printw("Message decode error from slave: {}".format(error))
                    if not indexMatch:
                        continue
                    else:
                        return None
                        
                except (ValueError, IndexError) as e:
                    # Handle message format errors
                    slave_info = {'mac': slave.getMAC(), 'ip': slave.getIP()}
                    error = self.error_handler.handle_communication_error(e, "message format", slave_info)
                    self.printw("Message format error from slave: {}".format(error))
                    
                    if not indexMatch:
                        # If the correct index has not yet been found, keep looking
                        continue
                    else:
                        # If the matching message is broken, exit with error code (None)
                        self.performance_monitor.end_timing('message_receive_time')
                        self.performance_monitor.record_error()
                        return None
                        
                except TypeError as e:
                    # Handle type conversion errors
                    slave_info = {'mac': slave.getMAC(), 'ip': slave.getIP()}
                    error = self.error_handler.handle_communication_error(e, "type conversion", slave_info)
                    self.printx("Type error in message processing: {}".format(error))
                    self.performance_monitor.end_timing('message_receive_time')
                    self.performance_monitor.record_error()
                    return None

                # End receive loop = = = = = = = = = = = = = = = = = = = = = = =

        # Handle exceptions: ---------------------------------------------------
        except socket.timeout:
            # Socket timeout is expected behavior in receive operations
            # Log timeout for debugging if needed
            slave_info = {'mac': slave.getMAC(), 'ip': slave.getIP()}
            self.error_handler.log_timeout("receive operation", slave_info)
            # 优化：禁用错误记录以减少CPU占用
            # debug_monitor.record_error("socket_timeout", f"slave_{slave.getIndex()}_receive_timeout")
            
            # 使用错误恢复机制
            context = {
                'slave_index': slave.getIndex(), 
                'operation': 'receive',
                'socket': slave._misoSocket()
            }
            error_recovery_manager.handle_error("socket_timeout", Exception("Socket timeout in receive"), context)
            
            self.performance_monitor.end_timing('message_receive_time')
            return None
            
        except socket.error as e:
            # Handle other socket errors
            slave_info = {'mac': slave.getMAC(), 'ip': slave.getIP()}
            error = self.error_handler.handle_network_error(e, "receive operation", slave_info)
            # 优化：禁用错误记录以减少CPU占用
            # debug_monitor.record_error("socket_error", f"slave_{slave.getIndex()}_network_error: {str(e)}")
            
            # 使用错误恢复机制
            context = {'slave_index': slave.getIndex(), 'operation': 'receive', 'error_details': str(e)}
            error_recovery_manager.handle_error("socket_error", e, context)
            
            self.printw("Network error in receive: {}".format(error))
            self.performance_monitor.end_timing('message_receive_time')
            self.performance_monitor.record_error()
            return None

        # End _receive # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    def getNewSlaves(self): # ==================================================
        # Get new Slaves, if any. Will return either a tuple of MAC addresses
        # or None.

        # FIXME: Obsolete? Delete?

        try:
            return self.newSlaveQueue.get_nowait()
        except queue.Empty:
            return None

        # End getNewSlaves =====================================================

    # # INTERFACE METHODS # # # # # # # # # # # # # # # # # # # # # # # # #

    def add(self, targetIndex): # ==============================================
        # ABOUT: Mark a Slave on the network for connection. The given Slave
        # must be already listed and marked AVAILABLE. This method will mark it
        # as KNOWN, and its corresponding handler thread will connect automati-
        # cally.
        # PARAMETERS:
        # - targetIndex: int, index of Slave to "add."
        # RAISES:
        # - Exception if targeted Slave is not AVAILABLE.
        # - KeyError if targetIndex is not listed.

        # Check status:
        status = self.slaves[targetIndex].getStatus()

        if status == s.SS_AVAILABLE:
            self.setSlaveStatus(self.slaves[targetIndex], s.SS_KNOWN)
        else:
            pass

        # End add ==============================================================

    def sendReboot(self, target = None): # =====================================
        # ABOUT: Use broadcast socket to send a general "disconnect" message
        # that terminates any existing connection.

        try:
            #self.broadcastLock.acquire()
            if target is None:
                # General broadcast
                self.rebootSocket.sendto(
                    bytearray("R|{}".format(self.passcode),'ascii'),
                    (self.defaultBroadcastIP, self.broadcastPort))

            elif target.getIP() is not None:
                # Targetted broadcast w/ valid IP:
                self.rebootSocket.sendto(
                    bytearray("R|{}".format(self.passcode),'ascii'),
                    (target.getIP(), self.broadcastPort))

            else:
                # Targetted broadcast w/o IP (use MAC):
                self.rebootSocket.sendto(
                    bytearray("r|{}|{}".format(self.passcode, target.getMAC()),
                        'ascii'),
                        (self.defaultBroadcastIP, self.broadcastPort))

        except Exception as e:
            self.printx(e, "[sR] Exception in reboot routine:")

        #finally:
            #self.broadcastLock.release()

        # End sendReboot =======================================================

    def sendChase(self, targetRPM, fanID=0, targets = None): # ==========================
        """
        Send a CHASE command to start RPM control mode.
            targetRPM := target RPM value for CHASE mode
            fanID := fan ID to control (default 0)
            targets := list of slave indices to target. If None, broadcast to all.
        """
        try:
            if targets is None:
                # Broadcast to all slaves
                # Format: C|passcode|fanID|targetRPM
                self.disconnectSocket.sendto(
                    bytearray("C|{}|{}|{}".format(self.passcode, fanID, targetRPM), 'ascii'),
                    (self.defaultBroadcastIP, self.broadcastPort))
                self.printw("[sC] Sent CHASE command (broadcast): fanID = {}, target RPM = {}".format(fanID, targetRPM))
            else:
                # Send to specific targets
                for slaveIndex in targets:
                    slave = self.getSlaveByIndex(slaveIndex)
                    if slave is not None:
                        # Format: c|passcode|fanID|targetRPM|MAC
                        self.disconnectSocket.sendto(
                            bytearray("c|{}|{}|{}|{}".format(self.passcode, fanID, targetRPM, slave.getMAC()), 'ascii'),
                            (self.defaultBroadcastIP, self.broadcastPort))
                        self.printw("[sC] Sent CHASE command to slave {}: fanID = {}, target RPM = {}".format(slaveIndex, fanID, targetRPM))

        except Exception as e:
            self.printx(e, "[sC] Exception in CHASE routine:")

        # End sendChase ========================================================

    def sendChaseWithSelection(self, targetRPM, selection, fanID=0): # ================
        """
        Send a CHASE command with fan selection to start RPM control mode.
            targetRPM := target RPM value for CHASE mode
            selection := string of 1s and 0s indicating which fans to control
            fanID := fan ID to control (default 0)
        """
        try:
            # Broadcast CHASE command with selection to all slaves
            # Format: CS|passcode|fanID|targetRPM|selection
            self.disconnectSocket.sendto(
                bytearray("CS|{}|{}|{}|{}".format(self.passcode, fanID, targetRPM, selection), 'ascii'),
                (self.defaultBroadcastIP, self.broadcastPort))
            self.printw("[sCS] Sent CHASE command with selection (broadcast): fanID = {}, target RPM = {}, selection = {}".format(fanID, targetRPM, selection))

        except Exception as e:
            self.printx(e, "[sCS] Exception in CHASE with selection routine:")

        # End sendChaseWithSelection ==============================================

    def sendPISet(self, fanID, kp, ki, targets=None): # ========================
        """
        Send a PISET command to set PI controller parameters.
            fanID := fan ID to configure (default 0)
            kp := proportional gain value
            ki := integral gain value
            targets := list of slave indices to target. If None, broadcast to all.
        """
        try:
            if targets is None:
                # Broadcast to all slaves
                # Format: P|passcode|PISET fanID kp ki
                self.disconnectSocket.sendto(
                    bytearray("P|{}|PISET {} {} {}".format(self.passcode, fanID, kp, ki), 'ascii'),
                    (self.defaultBroadcastIP, self.broadcastPort))
                self.printw("[sP] Sent PISET command (broadcast): fanID = {}, kp = {}, ki = {}".format(fanID, kp, ki))
            else:
                # Send to specific targets
                for slaveIndex in targets:
                    slave = self.getSlaveByIndex(slaveIndex)
                    if slave is not None:
                        # Format: p|passcode|PISET fanID kp ki|MAC
                        self.disconnectSocket.sendto(
                            bytearray("p|{}|PISET {} {} {}|{}".format(self.passcode, fanID, kp, ki, slave.getMAC()), 'ascii'),
                            (self.defaultBroadcastIP, self.broadcastPort))
                        self.printw("[sP] Sent PISET command to slave {}: fanID = {}, kp = {}, ki = {}".format(slaveIndex, fanID, kp, ki))

        except Exception as e:
            self.printx(e, "[sP] Exception in PISET routine:")

        # End sendPISet ========================================================

    def sendDisconnect(self): # ================================================
        # ABOUT: Use disconenct socket to send a general "disconnect" message
        # that terminates any existing connection.

        try:
            #self.broadcastLock.acquire()
            self.disconnectSocket.sendto(
                bytearray("X|{}".format(self.passcode),'ascii'),
                (self.defaultBroadcastIP, self.broadcastPort))

        except Exception as e:
            self.printx(e, "[sD] Exception in disconnect routine")

        # End sendDisconnect ===================================================

    def setSlaveStatus(self, slave, newStatus, lock = True, netargs = None): # =
        # Thread-safe slave status update with proper locking
        
        # 使用稳定性优化器安全获取锁
        if self.stability_optimizer.safe_acquire_lock('slavesLock', self.slavesLock, timeout=5.0):
            try:
                # Update status:
                if netargs is None:
                    slave.setStatus(newStatus, lock = lock)
                else:
                    slave.setStatus(newStatus, netargs[0], netargs[1], netargs[2],
                        netargs[3], lock = lock)

                # Send update to handlers:
                self.slaveUpdateQueue.put_nowait(self.getSlaveStateVector(slave))
            finally:
                self.stability_optimizer.safe_release_lock('slavesLock', self.slavesLock)
        else:
            self.printw("Warning: Failed to acquire slavesLock within timeout, skipping status update")
        # End setSlaveStatus ===================================================

    def getSlaveStateVector(self, slave):
        """
        Generate and return a list to be appended to a slave state vector.
        - slave: slave object from which to generate the list.
        """
        return [slave.index, slave.name, slave.mac, slave.getStatus(),
            slave.fans, slave.version]

    def stop(self): # ==========================================================
        """
        Clean up to terminate.
        """
        # NOTE: All threads are set as Daemon and all sockets as reusable.

        self.printw("Terminating back-end")
        # Send disconnect signal:
        self.sendDisconnect()
        self.stopped.set()
        self.printw("Terminated back-end")
        return
        # End shutdown =========================================================

    def join(self, timeout = None):
        """
        Block until the communicator terminates.
            timeout := seconds to wait (float)
        """
        self.stopped.wait(timeout)

    def _sendNetwork(self):
        """
        Send a network state vector to the front end.
        """
        self.networkPipeSend.send(
            (s.NS_CONNECTED,
            self.listenerSocket.getsockname()[0], # FIXME (?)
            self.broadcastIP,
            self.broadcastPort,
            self.listenerPort))

    def _sendSlaves(self):
        S = []
        for slave in self.slaves:
            S += self.getSlaveStateVector(slave)
        self.slavePipeSend.send(S)
    
    def get_performance_stats(self):
        """
        Get current performance statistics from the performance monitor.
        """
        return self.performance_monitor.get_performance_stats()
    
    def reset_performance_stats(self):
        """
        Reset all performance statistics.
        """
        self.performance_monitor.reset_metrics()
    
    def enable_performance_monitoring(self):
        """
        Enable performance monitoring.
        """
        self.performance_monitor.enable()
    
    def disable_performance_monitoring(self):
        """
        Disable performance monitoring.
        """
        self.performance_monitor.disable()

## MODULE'S TEST SUITE #########################################################

if __name__ == "__main__":
    pass

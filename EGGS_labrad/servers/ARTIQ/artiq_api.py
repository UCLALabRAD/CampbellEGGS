import numpy as np

from artiq.language import *
from artiq.coredevice import *
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
from artiq.coredevice.urukul import urukul_sta_rf_sw, CFG_PROFILE

from builtins import ConnectionAbortedError, ConnectionResetError


class ARTIQ_api(object):
    """
    An API for the ARTIQ box.
    Directly accesses the hardware on the box without having to use artiq_master.
    # todo: set version so we know what we're compatible with
    # todo: experiment with kernel invariants, fast-math, host_only, rpc, portable
    # todo: write sequence that pulls all dds values so we don't have to wait forever during dds client startup
    # todo: see if we can get initialization status of DDSs and initialize upon startup only if they are uninitialized
    """

    def autoreload(func):
        """
        A decorator for non-kernel functions that attempts to reset
        the connection to artiq_master if we lost it.
        """
        def inner(self, *args, **kwargs):
            try:
                res = func(self, *args, **kwargs)
                return res
            except (ConnectionAbortedError, ConnectionResetError) as e:
                try:
                    print('Connection aborted, resetting connection to artiq_master...')
                    self.reset()
                    res = func(self, *args, **kwargs)
                    return res
                except Exception as e:
                    raise e
        return inner

    def __init__(self, ddb_filepath):
        devices = DeviceDB(ddb_filepath)
        self.ddb_filepath = ddb_filepath
        self.device_manager = DeviceManager(devices)
        self.device_db = devices.get_device_db()
        self._getDevices()

    def stopAPI(self):
        """
        Closes any opened devices.
        """
        self.device_manager.close_devices()

    def reset(self):
        """
        Reestablishes a connection to artiq_master.
        """
        devices = DeviceDB(self.ddb_filepath)
        self.device_manager = DeviceManager(devices)
        self.device_db = devices.get_device_db()
        self._getDevices()


    # SETUP
    def _getDevices(self):
        """
        Gets necessary device objects.
        """
        # get core
        self.core = self.device_manager.get("core")
        self.core_dma = self.device_manager.get("core_dma")
        # store devices in dictionary where device
        # name is key and device itself is value
        self.ttlout_dict = {}
        self.ttlin_dict = {}
        self.ttlcounter_dict = {}
        self.dds_dict = {}
        self.urukul_dict = {}
        self.zotino = None
        self.fastino = None
        self.dacType = None
        self.sampler = None
        self.phaser = None

        # assign names and devices
        for name, params in self.device_db.items():
            # only get devices with named class
            if 'class' not in params:
                continue
            # set device as attribute
            devicetype = params['class']
            device = self.device_manager.get(name)
            if devicetype == 'TTLInOut':
                self.ttlin_dict[name] = device
            elif devicetype == 'TTLOut':
                self.ttlout_dict[name] = device
            elif devicetype == 'AD9910':
                self.dds_dict[name] = device
            elif devicetype == 'CPLD':
                self.urukul_dict[name] = device
            elif devicetype == 'Zotino':
                # need to specify both device types since
                # all kernel functions need to be valid
                self.zotino = device
                self.fastino = device
                self.dacType = devicetype
            elif devicetype == 'Fastino':
                self.fastino = device
                self.zotino = device
                self.dacType = devicetype
            elif devicetype == 'Sampler':
                self.sampler = device
            elif devicetype == 'Phaser':
                self.phaser = device
            elif devicetype == 'EdgeCounter':
                self.ttlcounter_dict[name] = device

        # tmp remove
        self._dds_channels = list(self.dds_dict.values())
        self._dds_boards = list(self.urukul_dict.values())

        yz0 = ['urukul0_ch{:d}'.format(i) for i in range(4)]
        yz1 = ['urukul1_ch{:d}'.format(i) for i in range(4)]
        for dev_name in (yz0+yz1):
            setattr(self, dev_name, self.device_manager.get(dev_name))

    def _initializeDevices(self):
        """
        Initialize devices that need to be initialized.
        """
        # initialize DDSs
        self.initializeDDSAll()
        # one-off device init
        self.initializeDAC()


    # PULSE SEQUENCING
    @kernel
    def record(self, sequencename):
        self.core.reset()
        with self.core_dma.record(sequencename):
            for i in range(50):
                with parallel:
                    self.ttlout_dict[0].pulse(1*ms)
                    self.ttlout_dict[1].pulse(1*ms)
                delay(1.0 * ms)

    def record2(self, ttl_seq, dds_seq, sequencename):
        """
        Processes the TTL and DDS sequence into a format
        more easily readable and processable by ARTIQ.
        """
        # TTL
        ttl_times = list(ttl_seq.keys())
        ttl_commands = list(ttl_seq.values())
        # DDS
        dds_times = list(dds_seq.keys())
        dds_commands = list(dds_seq.values())
        # send to kernel
        self._record(ttl_times, ttl_commands, dds_times, dds_commands, sequencename)

    @kernel
    def eraseSequence(self, sequencename):
        """
        Erase the given pulse sequence from DMA.
        """
        self.core.reset()
        self.core_dma.erase(sequencename)


    # DMA
    @autoreload
    def runDMA(self, handle_name):
        handle = self.core_dma.get_handle(handle_name)
        self._runDMA(handle)

    @kernel
    def _runDMA(self, handle):
        self.core.break_realtime()
        self.core_dma.playback_handle(handle)
        self.core.break_realtime()


    # TTL
    @autoreload
    def setTTL(self, ttlname, state):
        """
        Manually set the state of a TTL.
        """
        try:
            dev = self.ttlout_dict[ttlname]
        except KeyError:
            raise Exception('Invalid device name.')
        self._setTTL(dev, state)

    @kernel
    def _setTTL(self, dev, state):
        self.core.reset()
        if state:
            dev.on()
        else:
            dev.off()

    def getTTL(self, ttlname):
        """
        Manually set the state of a TTL.
        """
        try:
            dev = self.ttlin_dict[ttlname]
        except KeyError:
            raise Exception('Invalid device name.')
        self._getTTL(dev)

    @kernel
    def _getTTL(self, dev):
        self.core.reset()
        return dev.sample_get_nonrt()

    @autoreload
    def counterTTL(self, ttlname, time_us, trials):
        """
        Get the number of TTL input events for a given time, averaged over a number of trials.
        """
        try:
            dev = self.ttlcounter_dict[ttlname]
        except KeyError:
            raise Exception('Invalid device name.')
        # convert us to mu
        time_mu = self.core.seconds_to_mu(time_us * us)
        # create holding structures for counts
        setattr(self, "ttl_counts_array", np.zeros(trials))
        # get counts
        self._counterTTL(dev, time_mu, trials)
        # delete holding structure
        tmp_arr = self.ttl_counts_array
        delattr(self, "ttl_counts_array")
        return tmp_arr

    @kernel
    def _counterTTL(self, dev, time_mu, trials):
        self.core.break_realtime()
        for i in range(trials):
            self.core.break_realtime()
            dev.gate_rising_mu(time_mu)
            self._recordTTLCounts(dev.fetch_count(), i)

    @rpc(flags={"async"})
    def _recordTTLCounts(self, value, index):
        """
        Records values via rpc to minimize kernel overhead.
        """
        self.ttl_counts_array[index] = value

    # DDS
    @autoreload
    def initializeDDSAll(self):
        # initialize urukul cplds as well as dds channels
        device_list = list(self.urukul_dict.values())
        for device in device_list:
            self._initializeDDS(device)

    @autoreload
    def initializeDDS(self, dds_name):
        dev = self.dds_dict[dds_name]
        self._initializeDDS(dev)

    @kernel
    def _initializeDDS(self, dev):
        self.core.reset()
        dev.init()

    @autoreload
    def getDDSsw(self, dds_name):
        """
        Get the RF switch status of a DDS channel.
        """
        dev = self.dds_dict[dds_name]
        # get channel number of dds
        channel_num = dev.chip_select - 4
        # get board status register
        urukul_cfg = self._getUrukulStatus(dev.cpld)
        # extract switch register from status register
        sw_reg = urukul_sta_rf_sw(urukul_cfg)
        return (sw_reg >> channel_num) & 0x1

    @autoreload
    def setDDSsw(self, dds_name, state):
        """
        Set the RF switch of a DDS channel.
        """
        dev = self.dds_dict[dds_name]
        # get channel number of dds
        channel_num = dev.chip_select - 4
        # get board status register
        urukul_cfg = self._getUrukulStatus(dev.cpld)
        # extract switch register from status register
        sw_reg = urukul_sta_rf_sw(urukul_cfg)
        # insert new switch status
        sw_reg &= ~(0x1 << channel_num)
        sw_reg |= (state << channel_num)
        # set switch status for whole board
        self._setDDSsw(dev.cpld, sw_reg)

    @kernel
    def _setDDSsw(self, cpld, state):
        self.core.reset()
        cpld.cfg_switches(state)

    @autoreload
    def getDDS(self, dds_name):
        """
        Get the frequency, amplitude, and phase values
        (in machine units) of a DDS channel.
        """
        dev = self.dds_dict[dds_name]
        # read in waveform values
        profiledata = self._readDDS64(dev, 0x0E)
        # separate register values into ftw, asf, and pow
        ftw = profiledata & 0xFFFFFFFF
        pow = (profiledata >> 32) & 0xFFFF
        asf = (profiledata >> 48)
        # ftw = 0XFFFFFFFF means not initialized
        ftw = 0 if (ftw == 0xFFFFFFFF) else ftw
        # asf = -1 or 0x8b5 means amplitude has not been set
        asf = 0 if (asf < 0) or ((asf == 0x8b5) & (ftw == 0x0)) else asf & 0x3FFF
        return np.int32(ftw), np.int32(asf), np.int32(pow)

    @autoreload
    def setDDS(self, dds_name, param, val):
        """
        Manually set the frequency, amplitude, or phase values
        (in machine units) of a DDS channel.
        """
        dev = self.dds_dict[dds_name]
        # read in current parameters
        profiledata = self._readDDS64(dev, 0x0E)
        ftw = val if param == 'ftw' else (profiledata & 0xFFFFFFFF)
        asf = val if param == 'asf' else ((profiledata >> 48) & 0x3FFF)
        pow = val if param == 'pow' else ((profiledata >> 32) & 0xFFFF)
        # set DDS
        self._setDDS(dev, np.int32(ftw), np.int32(asf), np.int32(pow))

    @kernel
    def _setDDS(self, dev, ftw, asf, pow):
        self.core.reset()
        dev.set_mu(ftw, pow_=pow, asf=asf)

    @autoreload
    def getDDSatt(self, dds_name):
        """
        Set the DDS attenuation.
        """
        dev = self.dds_dict[dds_name]
        # get channel number of dds
        channel_num = dev.chip_select - 4
        att_reg = np.int32(self._getUrukulAtt(dev.cpld))
        # get only attenuation of channel
        return np.int32((att_reg >> (8 * channel_num)) & 0xff)

    @autoreload
    def setDDSatt(self, dds_name, att_mu):
        """
        Set the DDS attenuation.
        """
        dev = self.dds_dict[dds_name]
        # get channel number of dds
        channel_num = dev.chip_select - 4
        att_reg = self._setDDSatt(dev.cpld, channel_num, att_mu)

    @kernel
    def _setDDSatt(self, cpld, channel_num, att_mu):
        self.core.reset()
        cpld.bus.set_config_mu(0x0C, 32, 16, 2)
        # shift in zeros, shift out current value
        cpld.bus.write(0)
        cpld.bus.set_config_mu(0x0A, 32, 6, 2)
        delay_mu(10000)
        cpld.att_reg = cpld.bus.read()
        # remove old attenuator value for desired channel
        cpld.att_reg &= ~(0xff << (8 * channel_num))
        # add in new attenuator value
        cpld.att_reg |= (att_mu << (8 * channel_num))
        # shift in adjusted value and latch
        cpld.bus.write(cpld.att_reg)

    @autoreload
    def readDDS(self, dds_name, reg, length):
        """
        Read the value of a DDS register.
        """
        dev = self.dds_dict[dds_name]
        if length == 16:
            return self._readDDS16(dev, reg)
        elif length == 32:
            return self._readDDS32(dev, reg)
        elif length == 64:
            return self._readDDS64(dev, reg)

    @kernel
    def _readDDS16(self, dev, reg):
        self.core.reset()
        return dev.read16(reg)

    @kernel
    def _readDDS32(self, dev, reg):
        self.core.reset()
        return dev.read32(reg)

    @kernel
    def _readDDS64(self, dev, reg):
        self.core.reset()
        return dev.read64(reg)


    # DDS QUICK GET
    @autoreload
    def getDDSAll(self):
        """
        Quickly get frequency, amplitude, attenuation, and switch values
        (in machine units) for all DDS channels.
        """
        # create structures to hold params
        dds_params_processed = np.zeros([len(self.dds_dict), 4], dtype=np.int32)
        setattr(self, "channel_profiledata", [])
        setattr(self, "board_sw", [])
        setattr(self, "board_att", [])

        # get params!
        self._getDDSAll()

        # process channel params
        for i, profiledata in enumerate(self.channel_profiledata):
            ftw = profiledata & 0xFFFFFFFF
            ftw = 0 if (ftw == 0xFFFFFFFF) else np.int32(ftw)
            asf = profiledata >> 48
            asf = 0 if ((asf < 0) or ((asf == 0x8b5) & (ftw == 0x0))) else np.int32(asf & 0x3FFF)
            dds_params_processed[i][:2] = [ftw, asf]

        # process attenuation state
        board_att_tmp = []
        for i, att_state in enumerate(self.board_att):
            att_state = '{:08x}'.format(att_state)
            board_att_tmp += [int(att_state[i: i+2], base=16) for i in range(0, len(att_state), 2)][::-1]
        dds_params_processed[:, 2] = board_att_tmp

        # process switch state
        board_sw_tmp = []
        for i, sw_state in enumerate(self.board_sw):
            sw_state_processed = reversed('{:04b}'.format(sw_state))
            board_sw_tmp += list(map(int, sw_state_processed))
        dds_params_processed[:, 3] = board_sw_tmp

        # delete holding structures
        delattr(self, "channel_profiledata")
        delattr(self, "board_sw")
        delattr(self, "board_att")

        return dds_params_processed

    @kernel
    def _getDDSAll(self):
        self.core.break_realtime()

        # read channel parameters
        for dev_ad9910 in self._dds_channels:
            self._recordParamsChannel(dev_ad9910.read64(0x0E))
            self.core.break_realtime()

        # read board parameters
        for dev_cpld in self._dds_boards:
            cpld_sta_reg = dev_cpld.sta_read()
            self.core.break_realtime()
            cpld_att_reg = dev_cpld.get_att_mu()
            self._recordParamsBoard(cpld_sta_reg, cpld_att_reg)
            self.core.break_realtime()

    @rpc(flags={"async"})
    def _recordParamsChannel(self, profiledata):
        self.channel_profiledata.append(profiledata)

    @rpc(flags={"async"})
    def _recordParamsBoard(self, sw_state, att_state):
        self.board_sw.append(urukul_sta_rf_sw(sw_state))
        self.board_att.append(np.uintc(att_state))

    #
    # # DDS PROFILE/RAM
    # def getDDSProfile(self, dds_name, profile_num):
    #     """
    #     Get the profile number of a DDS channel.
    #     """
    #     dev = self.dds_dict[dds_name]
    #     # get channel number of dds
    #     # channel_num = dev.chip_select - 4
    #     # # get board status register
    #     # urukul_cfg = self._getUrukulStatus(dev.cpld)
    #     # # extract switch register from status register
    #     # sw_reg = urukul_sta_rf_sw(urukul_cfg)
    #     # return (sw_reg >> channel_num) & 0x1
    #     # self.bus.set_config_mu(SPI_CONFIG | spi.SPI_END, 24,
    #     #                        SPIT_CFG_WR, CS_CFG)
    #     # self.bus.write(cfg << 8)
    #     # self.cfg_reg = cfg


    # URUKUL
    @autoreload
    def initializeUrukul(self, urukul_name):
        """
        Initialize an Urukul board.
        """
        dev = self.urukul_dict[urukul_name]
        self._initializeUrukul(dev)

    @kernel
    def _initializeUrukul(self, dev):
        self.core.reset()
        dev.init()

    @kernel
    def _getUrukulStatus(self, cpld):
        """
        Get the status register of an Urukul board.
        """
        self.core.reset()
        return cpld.sta_read()

    @kernel
    def _getUrukulAtt(self, cpld):
        """
        Get the attenuation register of an Urukul board.
        """
        self.core.reset()
        return cpld.get_att_mu()

    # @kernel
    # def _getUrukulProfile(self, cpld):
    #     """
    #     Get the profile register of an Urukul board.
    #     """
    #     self.core.reset()
    #     return (cpld.cfg_reg >> CFG_PROFILE) & 0x8


    # DAC/ZOTINO
    @autoreload
    def initializeDAC(self):
        self._initializeDAC()

    @kernel
    def _initializeDAC(self):
        """
        Initialize the DAC.
        """
        self.core.reset()
        self.zotino.init()

    @autoreload
    def setZotino(self, channel_num, volt_mu):
        self._setZotino(channel_num, volt_mu)

    @kernel
    def _setZotino(self, channel_num, volt_mu):
        """
        Set the voltage of a DAC register.
        """
        self.core.reset()
        self.zotino.write_dac_mu(channel_num, volt_mu)
        self.zotino.load()

    @autoreload
    def setZotinoGain(self, channel_num, gain_mu):
        self._setZotinoGain(channel_num, gain_mu)

    @kernel
    def _setZotinoGain(self, channel_num, gain_mu):
        """
        Set the gain of a DAC channel.
        """
        self.core.reset()
        self.zotino.write_gain_mu(channel_num, gain_mu)
        self.zotino.load()

    @autoreload
    def setZotinoOffset(self, channel_num, volt_mu):
        self._setZotinoOffset(channel_num, volt_mu)

    @kernel
    def _setZotinoOffset(self, channel_num, volt_mu):
        """
        Set the voltage of a DAC offset register.
        """
        self.core.reset()
        self.zotino.write_offset_mu(channel_num, volt_mu)
        self.zotino.load()

    @autoreload
    def setZotinoGlobal(self, word):
        self._setZotinoGlobal(word)

    @kernel
    def _setZotinoGlobal(self, word):
        """
        Set the OFSx registers on the AD5372.
        """
        self.core.reset()
        self.zotino.write_offset_dacs_mu(word)

    @autoreload
    def readZotino(self, channel_num, address):
        return self._setZotinoGlobal(channel_num, address)

    @kernel
    def _readZotino(self, channel_num, address):
        """
        Read the value of one of the DAC registers.
        :param channel_num: Channel to read from
        :param address: Register to read from
        :return: the value of the register
        """
        self.core.reset()
        reg_val = self.zotino.read_reg(channel_num, address)
        return reg_val


    # FASTINO
    @autoreload
    def initializeFastino(self):
        self._initializeFastino()

    @kernel
    def _initializeFastino(self):
        """
        Initialize the Fastino.
        """
        self.core.break_realtime()
        self.fastino.init()

    @autoreload
    def setFastino(self, channel_num, volt_mu):
        self._setFastino(channel_num, volt_mu)

    @kernel
    def _setFastino(self, channel_num, volt_mu):
        """
        Set the voltage of a Fastino register.
        """
        self.core.reset()
        self.fastino.set_dac_mu(channel_num, volt_mu)
        self.fastino.update(1 << channel_num)
        self.core.break_realtime()

    @autoreload
    def readFastino(self, addr):
        return self._readFastino(addr)

    @kernel
    def _readFastino(self, addr):
        self.core.break_realtime()
        return self.fastino.read(addr)

    @autoreload
    def continuousFastino(self, channel_num):
        self._continuousFastino(channel_num)

    @kernel
    def _continuousFastino(self, channel_num):
        """
        Allows a Fastino channel to be updated continuously regardless of incoming data.
        """
        self.core.break_realtime()
        self.fastino.set_continuous(1 << channel_num)

    # todo: fastino interpolating/CIC


    # SAMPLER
    @autoreload
    def initializeSampler(self):
        """
        Initialize the Sampler.
        """
        self._initializeSampler()

    @kernel
    def _initializeSampler(self):
        """
        Initialize the Sampler.
        """
        self.core.reset()
        self.sampler.init()

    @autoreload
    def setSamplerGain(self, channel_num, gain_mu):
        """
        Set the gain for a sampler channel.
        :param channel_num: Channel to set
        :param gain_mu: Register to read from
        :return: the value of the register
        """
        self._setSamplerGain(channel_num, gain_mu)

    @kernel
    def _setSamplerGain(self, channel_num, gain_mu):
        self.core.reset()
        self.sampler.set_gain_mu(channel_num, gain_mu)

    @autoreload
    def getSamplerGains(self):
        # get raw gain register
        gains = self._getSamplerGains()
        gains = ('{:016b}'.format(gains))
        # convert to machine units
        gain_status_tmp = []
        gain_status_tmp += [int(gains[i: i+2], base=2) for i in range(0, len(gains), 2)]
        # reverse only at end since gains are ordered the other way
        gain_status_tmp = gain_status_tmp[::-1]
        return gain_status_tmp

    @kernel
    def _getSamplerGains(self):
        """
        Get the gain of all sampler channels.
        :return: the sample channel gains.
        """
        self.core.reset()
        return self.sampler.gains

    @autoreload
    def readSampler(self, rate_hz, samples):
        setattr(self, "sampler_dataset", np.zeros((samples, 8), dtype=np.int32))
        setattr(self, "sampler_holder", np.zeros(8, dtype=np.int32))
        # convert rate to mu
        time_delay_mu = self.core.seconds_to_mu(1 / rate_hz)
        # read samples!
        self._readSampler(time_delay_mu, samples)
        # delete holding structure
        tmp_arr = self.sampler_dataset
        delattr(self, "sampler_dataset")
        delattr(self, "sampler_holder")
        return tmp_arr

    @kernel
    def _readSampler(self, time_delay_mu, samples):
        self.core.reset()
        for i in range(samples):
            with parallel:
                with sequential:
                    self.sampler.sample_mu(self.sampler_holder)
                    self._recordSamplerValues(i, self.sampler_holder)
                delay_mu(time_delay_mu)

    @rpc(flags={"async"})
    def _recordSamplerValues(self, i, value_arr):
        """
        Records values via rpc to minimize kernel overhead.
        """
        self.sampler_dataset[i] = value_arr


from common.lib.servers.Pulser2.pulse_sequences.pulse_sequence import pulse_sequence
from labrad.units import WithUnit as U


class shelving_state_detection(pulse_sequence):

    required_parameters = [
        ('ShelvingStateDetection', 'duration'),
        ('ShelvingStateDetection', 'repump_power'),
        ('ShelvingStateDetection', 'detuning'),
        ('ShelvingStateDetection', 'CW_power'),
        ('ShelvingStateDetection', 'repititions'),
        ('ShelvingStateDetection', 'state_readout_threshold'),
        ('MicrowaveInterogation', 'power'),
        ('Transitions', 'main_cooling_369'),
        ('ddsDefaults', 'doppler_cooling_freq'),
        ('ddsDefaults', 'doppler_cooling_power'),
        ('ddsDefaults', 'repump_935_freq'),
        ('ddsDefaults', 'qubit_dds_freq')
                            ]

    def sequence(self):
        p = self.parameters

        # standard readout count TTL, provides number of detected photons
        self.addTTL('ReadoutCount',
                    self.start,
                    p.ShelvingStateDetection.duration)

        # provides timetags
        self.addTTL('TimeResolvedCount',
                    self.start,
                    p.ShelvingStateDetection.duration)

        self.addDDS('935SP',
                    self.start,
                    p.ShelvingStateDetection.duration,
                    p.ddsDefaults.repump_935_freq,
                    p.ShelvingStateDetection.repump_power)

        self.addDDS('369DP',
                    self.start,
                    p.ShelvingStateDetection.duration,
                    p.Transitions.main_cooling_369/2.0 + U(200.0, 'MHz') + p.ShelvingStateDetection.detuning/2.0,
                    p.ShelvingStateDetection.CW_power)

        self.addDDS('DopplerCoolingSP',
                    self.start,
                    p.ShelvingStateDetection.duration,
                    p.ddsDefaults.doppler_cooling_freq,
                    p.ddsDefaults.doppler_cooling_power)

        self.end = self.start + p.ShelvingStateDetection.duration

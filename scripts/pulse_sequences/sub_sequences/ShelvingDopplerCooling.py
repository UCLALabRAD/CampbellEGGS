from common.lib.servers.Pulser2.pulse_sequences.pulse_sequence import pulse_sequence
from labrad.units import WithUnit as U


class shelving_doppler_cooling(pulse_sequence):

    required_parameters = [
        ('DopplerCooling', 'cooling_power'),
        ('DopplerCooling', 'repump_power'),
        ('DopplerCooling', 'detuning'),
        ('Shelving_Doppler_Cooling', 'duration'),
        ('Transitions', 'main_cooling_369'),
        ('ddsDefaults', 'doppler_cooling_freq')
                           ]

    def sequence(self):
        p = self.parameters

        self.addDDS('DopplerCoolingSP',
                    self.start,
                    p.Shelving_Doppler_Cooling.duration,
                    p.ddsDefaults.doppler_cooling_freq,
                    U(-9.0, 'dBm'))

        self.addDDS('369DP',
                    self.start,
                    p.Shelving_Doppler_Cooling.duration,
                    p.Transitions.main_cooling_369/2.0 + U(200.0, 'MHz') + p.DopplerCooling.detuning/2.0,
                    p.DopplerCooling.cooling_power)

        self.addDDS('935SP',
                    self.start,
                    p.Shelving_Doppler_Cooling.duration,
                    U(320.0, 'MHz'),
                    p.DopplerCooling.repump_power)

        self.addDDS('760SP',
                    self.start,
                    p.Shelving_Doppler_Cooling.duration,
                    U(160.0, 'MHz'),
                    U(-2.0,  'dBm'))

        self.addDDS('760SP2',
                    self.start,
                    p.Shelving_Doppler_Cooling.duration,
                    U(160.0, 'MHz'),
                    U(6.0,  'dBm'))

        self.addTTL('ReadoutCount', self.start, p.Shelving_Doppler_Cooling.duration)

        self.end = self.start + p.Shelving_Doppler_Cooling.duration

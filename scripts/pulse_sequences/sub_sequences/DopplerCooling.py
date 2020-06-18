from common.lib.servers.Pulser2.pulse_sequences.pulse_sequence import pulse_sequence
from labrad.units import WithUnit as U


class doppler_cooling(pulse_sequence):

    required_parameters = [
        ('DopplerCooling', 'cooling_power'),
        ('DopplerCooling', 'repump_power'),
        ('DopplerCooling', 'detuning'),
        ('DopplerCooling', 'duration'),
        ('Transitions', 'main_cooling_369'),
        ('ddsDefaults', 'doppler_cooling_freq'),
        ('ddsDefaults', 'doppler_cooling_power'),
        ('ddsDefaults', 'repump_935_freq'),
        ('MicrowaveInterogation', 'power')
                           ]

    def sequence(self):
        p = self.parameters

        self.addDDS('DopplerCoolingSP',
                    self.start,
                    p.DopplerCooling.duration,
                    p.ddsDefaults.doppler_cooling_freq,
                    p.ddsDefaults.doppler_cooling_power)

        self.addDDS('369DP',
                    self.start,
                    p.DopplerCooling.duration,
                    p.Transitions.main_cooling_369/2.0 + U(200.0, 'MHz') + p.DopplerCooling.detuning/2.0,
                    p.DopplerCooling.cooling_power)

        self.addDDS('935SP',
                    self.start,
                    p.DopplerCooling.duration,
                    p.ddsDefaults.repump_935_freq,
                    p.DopplerCooling.repump_power)

        #self.addTTL('MicrowaveTTL',
        #            self.start,
        #            p.DopplerCooling.duration)
        self.addDDS('Microwave_qubit',
                    self.start,
                    p.DopplerCooling.duration,
                    U(362.0, 'MHz'),
                    p.MicrowaveInterogation.power)

        self.end = self.start + p.DopplerCooling.duration

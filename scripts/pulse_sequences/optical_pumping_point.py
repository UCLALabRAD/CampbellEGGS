from common.lib.servers.Pulser2.pulse_sequences.pulse_sequence import pulse_sequence
from sub_sequences.DopplerCooling import doppler_cooling
from sub_sequences.TurnOffAll import turn_off_all
from sub_sequences.OpticalPumping import optical_pumping
from sub_sequences.StandardStateDetection import standard_state_detection
from sub_sequences.ShelvingDopplerCooling import shelving_doppler_cooling
from sub_sequences.ShelvingStateDetection import shelving_state_detection
from sub_sequences.Deshelving import deshelving

class optical_pumping_point(pulse_sequence):

    required_subsequences = [doppler_cooling, standard_state_detection, turn_off_all
                             , optical_pumping, shelving_doppler_cooling, shelving_state_detection,
                             deshelving]

    required_parameters = [
        ('OpticalPumping', 'method'),
        ('Modes', 'state_detection_mode')
                           ]

    def sequence(self):
        p = self.parameters

        if p.OpticalPumping.method == 'Standard':
            self.addSequence(doppler_cooling)
            self.addSequence(optical_pumping)
            self.addSequence(standard_state_detection)

        elif p.OpticalPumping.method == 'QuadrupoleOnly':
            if p.Modes.state_detection_mode == 'Shelving':
                self.addSequence(shelving_doppler_cooling)
                self.addSequence(optical_pumping)
                self.addSequence(shelving_state_detection)
                self.addSequence(deshelving)
            if p.Modes.state_detection_mode == 'Standard':
                self.addSequence(doppler_cooling)
                self.addSequence(optical_pumping)
                self.addSequence(standard_state_detection)
                self.addSequence(deshelving)
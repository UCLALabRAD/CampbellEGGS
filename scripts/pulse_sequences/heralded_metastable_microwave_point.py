from common.lib.servers.Pulser2.pulse_sequences.pulse_sequence import pulse_sequence
from sub_sequences.MicrowaveInterogation import microwave_interogation
from sub_sequences.MetastableMicrowaveInterogation import metastable_microwave_interogation
from sub_sequences.TurnOffAll import turn_off_all
from sub_sequences.MetastableStateDetection import metastable_state_detection
from deprecated.deprecated_sub_sequences.ShelvingDopplerCooling import shelving_doppler_cooling
from sub_sequences.OpticalPumping import optical_pumping
from sub_sequences.Shelving import shelving
from sub_sequences.Deshelving import deshelving
from sub_sequences.HeraldedStatePreparation import heralded_state_preparation


class heralded_metastable_microwave_point(pulse_sequence):

    required_subsequences = [turn_off_all, metastable_microwave_interogation,
                             metastable_state_detection, optical_pumping, shelving,
                             shelving_doppler_cooling, deshelving, microwave_interogation,
                             heralded_state_preparation]

    required_parameters = [
        ]

    def sequence(self):

        self.addSequence(turn_off_all)
        self.addSequence(shelving_doppler_cooling)  # readout counts call 1
        self.addSequence(optical_pumping)
        self.addSequence(microwave_interogation)
        self.addSequence(shelving)
        self.addSequence(heralded_state_preparation)  # readout counts call 2
        self.addSequence(metastable_microwave_interogation)
        self.addSequence(metastable_state_detection)  # readout counts call 3
        self.addSequence(deshelving)

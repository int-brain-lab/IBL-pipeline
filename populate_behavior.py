import numpy as np
import datajoint as dj
from ibl import reference, acquisition, subject, behavior, ephys

behavior.Eye.populate()
behavior.Wheel.populate()
behavior.WheelMoveSet.populate()
behavior.SparseNoise.populate()
behavior.SpontaneousTimeSet.populate()
behavior.Lick.populate()
behavior.TrialSet.populate()
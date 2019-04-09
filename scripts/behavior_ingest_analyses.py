import time
from ibl_pipeline import subject, acquisition, data, behavior

start = time.time()
behavior.CompleteTrialSession.populate(suppress_errors=True)
behavior.TrialSet.populate(display_progress=True, suppress_errors=True)
end = time.time()

print(end-start)

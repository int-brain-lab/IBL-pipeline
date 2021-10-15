import datajoint as dj
from os import path, environ
from .. import subject, acquisition, ephys, histology
from . import histology_plotting as hplt
from .figure_model import PngFigure, GifFigure
import boto3

from .. import one, mode


if mode == 'public':
    root_path = 'public'
else:
    root_path = ''

schema = dj.schema(dj.config.get('database.prefix', '') +
                   'ibl_plotting_histology')


# get external bucket
store = dj.config['stores']['plotting']
s3 = boto3.resource(
    's3',
    aws_access_key_id=store['access_key'],
    aws_secret_access_key=store['secret_key'])

bucket = s3.Bucket(store['bucket'])


@schema
class SubjectSpinningBrain(dj.Imported):
    definition = """
    -> subject.Subject
    ---
    subject_spinning_brain_link    : varchar(255)
    """
    # only populate those subjects with resolved trajectories
    key_source = subject.Subject & histology.ProbeTrajectory

    def make(self, key):
        subject_nickname = (subject.Subject & key).fetch1('subject_nickname')
        trajs = one.alyx.rest('trajectories', 'list', subject=subject_nickname,
                              provenance='Ephys Aligned Histology Track')

        fig = GifFigure(
            hplt.generate_spinning_brain_frames, trajs)

        fig_link = path.join(
            root_path, 'subject_spinning_brain',
            str(key['subject_uuid']) + '.gif'
        )

        fig.upload_to_s3(bucket, fig_link)
        self.insert1(dict(**key, subject_spinning_brain_link=fig_link))


@schema
class ProbeTrajectoryCoronal(dj.Imported):
    definition = """
    -> ephys.ProbeInsertion
    ---
    probe_trajectory_coronal_link    : varchar(255)
    """
    # only populate probe insertions with resolved trajectories
    key_source = ephys.ProbeInsertion & histology.ProbeTrajectory

    def make(self, key):

        eid = str((acquisition.Session & key).fetch1('session_uuid'))
        probe_label = (ephys.ProbeInsertion & key).fetch1('probe_label')

        fig = PngFigure(
            hplt.probe_trajectory_coronal,
            dict(eid=eid, probe_label=probe_label, one=one),
            dpi=100, figsize=[6, 4], axes_off=False)

        fig_link = path.join(
            root_path, 'probe_trajectory_coronal',
            str(key['subject_uuid']),
            key['session_start_time'].strftime('%Y-%m-%dT%H:%M:%S'),
            str(key['probe_idx']) + '.png'
        )

        fig.upload_to_s3(bucket, fig_link)

        self.insert1(dict(**key, probe_trajectory_coronal_link=fig_link))

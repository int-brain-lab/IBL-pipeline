from ibl_pipeline.ingest import subject as subject_ingest
from ibl_pipeline.ingest import alyxraw
from ibl_pipeline import subject
import datajoint as dj
import datetime

from tqdm import tqdm

if __name__ == '__main__':

    # ========= update all subjects fields in the subject shadow table ==============
    for subj in tqdm((subject_ingest.Subject).fetch('KEY'), position=0):

        # fetch corresponding entry in alyxraw table
        alyxraw.AlyxRaw & dict(uuid=subj['subject_uuid'])
        subj_ingest = subject_ingest.Subject & \
            dict(subject_uuid=subj['subject_uuid'])

        sex, dob, line, strain, source = subj_ingest.fetch1(
            'sex', 'subject_birth_date', 'subject_line',
            'subject_strain', 'subject_source')

        # ---------------- sex update -------------------
        try:
            sex_new = (alyxraw.AlyxRaw.Field &
                    dict(uuid=subj['subject_uuid'],
                            fname='sex')).fetch1('fvalue')
        except Exception:
            continue

        if sex_new == 'None':
            sex_new = None

        if sex != sex_new:
            dj.Table._update(subj_ingest, 'sex', sex_new)
            if sex and sex != 'U':
                print(f'updated field "sex" for one entry {subj}, \
                        original: {sex}, new: {sex_new}')

        # ---------------- dob update ------------------
        dob_new = (alyxraw.AlyxRaw.Field &
                dict(uuid=subj['subject_uuid'],
                        fname='birth_date')).fetch1('fvalue')

        if dob_new == 'None':
            dob_new = None
        else:
            dob_new = datetime.datetime.strptime(dob_new, '%Y-%m-%d').date()

        if dob != dob_new:
            if dob_new:
                dj.Table._update(subj_ingest, 'subject_birth_date', dob_new)
            if dob:
                dob_str = dob.strftime('%Y-%m-%d')
            else:
                dob_str = None
            if dob_new:
                dob_new_str = dob_new.strftime('%Y-%m-%d')
            else:
                dob_new_str = None

            if dob:
                print(f'updated field "birth date" for one entry {subj}, \
                        original: {dob_str}, new: {dob_new_str}')

        # --------------- line update -------------------
        line_uuid = (alyxraw.AlyxRaw.Field &
                    dict(uuid=subj['subject_uuid'],
                        fname='line')).fetch1('fvalue')

        # fetch actual line
        if line_uuid == 'None':
            line_new = None
        else:
            line_new = (subject_ingest.Line & dict(line_uuid=line_uuid)).fetch1(
                'line_name')

        if line_new != line:
            if line_new:
                dj.Table._update(subj_ingest, 'subject_line', line_new)
            if line:
                print(f'updated field "line" for one subject {subj}, \
                        original: {line}, new: {line_new}')

        # ---------------- strain update ----------------
        strain_uuid = (alyxraw.AlyxRaw.Field &
                    dict(uuid=subj['subject_uuid'],
                            fname='strain')).fetch1('fvalue')
        if strain_uuid == 'None':
            strain_new = None
        else:
            # fetch actual strain
            strain_new = (subject_ingest.Strain &
                        dict(strain_uuid=strain_uuid)).fetch1(
                'strain_name')

        if strain != strain_new:
            dj.Table._update(subj_ingest, 'subject_strain', strain_new)
            if strain:
                print(f'updated field "strain" for one subject {subj}, \
                        original: {strain}, new: {strain_new}')

        # ----------------- source update ----------------
        source_uuid = (alyxraw.AlyxRaw.Field &
                    dict(uuid=subj['subject_uuid'],
                            fname='source')).fetch1('fvalue')

        if source_uuid == 'None':
            source_new = None
        else:
            # fetch actual source
            source_new = (subject_ingest.Source &
                        dict(source_uuid=source_uuid)).fetch1(
                'source_name')

        if source != source_new:
            dj.Table._update(subj_ingest, 'subject_source', source_new)
            if source:
                print(f'updated field "source" for one subject {subj}, \
                        original: {source}, new: {source_new}')


    # =========== update all subjects in the subject real table ==================

    # find out the overlap of shadow subject table and main subject table

    for subj in tqdm((subject.Subject &
                    subject_ingest.Subject.proj()).fetch('KEY'),
                    position=0):

        subj_real = subject.Subject & subj

        sex, dob, line, strain, source = subj_real.fetch1(
            'sex', 'subject_birth_date', 'subject_line',
            'subject_strain', 'subject_source')

        sex_new, dob_new, line_new, strain_new, source_new = \
            (subject_ingest.Subject & subj).fetch1(
                'sex', 'subject_birth_date', 'subject_line',
                'subject_strain', 'subject_source')

        if sex_new != sex:
            dj.Table._update(subj_real, 'sex', sex_new)
            if sex and sex != 'U':
                print(f'updated field "sex" for one entry {subj}, \
                        original: {sex}, new: {sex_new}')

        if dob != dob_new:
            if dob_new:
                dj.Table._update(subj_real, 'subject_birth_date', dob_new)
            if dob:
                dob_str = dob.strftime('%Y-%m-%d')
            else:
                dob_str = None
            if dob_new:
                dob_new_str = dob_new.strftime('%Y-%m-%d')
            else:
                dob_new_str = None

            if dob:
                print(f'updated field "birth date" for one entry {subj}, \
                        original: {dob_str}, new: {dob_new_str}')

        if line_new != line:
            if line_new:
                dj.Table._update(subj_real, 'subject_line', line_new)
            if line:
                print(f'updated field "line" for one subject {subj}, \
                        original: {line}, new: {line_new}')

        if strain != strain_new:
            dj.Table._update(subj_real, 'subject_strain', strain_new)
            if strain:
                print(f'updated field "strain" for one subject {subj}, \
                        original: {strain}, new: {strain_new}')

        if source != source_new:
            dj.Table._update(subj_real, 'subject_source', source_new)
            if source:
                print(f'updated field "source" for one subject {subj}, \
                        original: {source}, new: {source_new}')

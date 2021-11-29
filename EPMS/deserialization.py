import pandas as pd
import music21


def get_transpose_interval_from_C(ks):
    if ks is None:
        return None

    if ks != 'C' and ks != 'a':
        if ks.mode == 'major':
            return music21.interval.Interval(music21.pitch.Pitch('C'), ks.tonic)
        elif ks.mode == 'minor':
            return music21.interval.Interval(music21.pitch.Pitch('a'), ks.tonic)


def get_continuous(arr):
    """Receives a list of tuples and returns a list of lists of tuples.
    Each list is split given the following criteria:
    1) The first element of each tuple of the list are the same
    2) The second element of each tuple of the list are in crescent order and
    Example:
        [(1,1), (1,2), (2,3), (2,4), (1,6), (1,7), (1,8)] ->
        [[(1, 1), (1, 2)], [(2, 3), (2, 4)], [(1, 6), (1, 7), (1, 8)]]
    """
    on_frames = []
    pivot = 0
    frame_list = [arr[pivot]]
    for i in range(1, len(arr)):
        # if it meets the criteria
        if arr[i][1] == arr[i-1][1]+1 and arr[i][0] == arr[pivot][0]:
            frame_list.append(arr[i])
        # create a new list
        else:
            on_frames.append(frame_list)
            frame_list = [arr[i]]
            pivot = i
        # if it's the last element you have to append the list or you'll lose it
        if i == len(arr)-1:
            on_frames.append(frame_list)
    return on_frames


def measure(m_metric, m_environment, m_performance, SETTINGS):
    """Deserialize a single multi hot encoding measure to a music21 measure"""
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    deserialized_measure = music21.stream.Measure(number=int(m_metric.MEASURE.iloc[0]))

    # get info about the first frame
    # and considering it as the
    # 'Main' info of the song
    measure_ks = m_environment.ORIGINAL_KS.mode()[0]
    measure_ts = m_environment.TS.mode()[0]
    measure_tempo = m_environment.TEMPO.mode()[0]

    met_perf_concat = pd.concat([m_metric.reset_index(), m_performance.reset_index()], axis=1)
    ks = music21.key.Key(measure_ks)
    transpose_int = get_transpose_interval_from_C(ks)
    deserialized_measure.append(ks)

    deserialized_measure.append(music21.tempo.MetronomeMark(number=measure_tempo,
                                                            referent='quarter'))
    ts = music21.meter.TimeSignature(measure_ts)
    deserialized_measure.append(ts)

    #
    #   PERFORM DESERIALIZATION
    #

    # decode the measure data, note by note
    for measure_note in m_performance.columns:
        # filter the frames where the current note is on
        on_frames = met_perf_concat.loc[met_perf_concat.loc[:, measure_note] != False, measure_note]
        if not on_frames.empty:
            frames_volumes = [(list(on_frames)[i], list(on_frames.index)[i]) for i in range(len(on_frames))]
            on_frames_list = get_continuous(frames_volumes)
            for frame_list in on_frames_list:
                note_obj = music21.note.Note(nameWithOctave=measure_note)
                this_note_on_frames = []

                # iterate over frames
                for volume_tuple in frame_list:
                    this_note_on_frames.append(volume_tuple)
                    # if it's the last frame, get the offset, the velocity and the duration of the note
                    if volume_tuple[1] == frame_list[-1][1]:
                        # get the volume of the note
                        note_obj.volume.velocityScalar = volume_tuple[0]
                        # get the start frame of the note
                        beat_offset = (this_note_on_frames[0][1] / SETTINGS.RESOLUTION)
                        note_obj.offset = beat_offset
                        # get the duration of the note
                        beat_dur = len(this_note_on_frames) / SETTINGS.RESOLUTION
                        note_obj.duration.quarterLength = beat_dur
                        # insert into measure
                        deserialized_measure.insert(note_obj)
                        this_note_on_frames = []

    # transpose it back to the original ks
    deserialized_measure.transpose(transpose_int, inPlace=True)

    # insert rests in between the notes
    deserialized_measure.makeRests(fillGaps=False, inPlace=True)

    return deserialized_measure


def instrument(SETTINGS, INSTRUMENT_BLOCK, METRIC_BLOCK, ENVIRONMENT_BLOCK, PERFORMANCE_BLOCK, save_as=None):
    """Deserialize an instrument line"""
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    # M21 object to be returned
    deserialized_part = music21.stream.Part()

    part_name = INSTRUMENT_BLOCK.NAME
    inst_name = INSTRUMENT_BLOCK.INSTRUMENT
    midi_program = INSTRUMENT_BLOCK.MIDI_PROGRAM
    inst_sound = INSTRUMENT_BLOCK.SOUND

    # set instrument
    m21_inst = music21.instrument.instrumentFromMidiProgram(midi_program)
    m21_inst.instrumentSound = inst_sound

    deserialized_part.insert(0, m21_inst)

    # total number of measures (bars)
    # in this part
    n_measures = max(set(METRIC_BLOCK.MEASURE))

    # deserialize measures
    #
    # iterate over measures (bars)
    for measure_index in range(1, n_measures + 1):

        measure_indexes = METRIC_BLOCK.loc[METRIC_BLOCK['MEASURE'] == measure_index]
        measure_indexes = measure_indexes.index

        measure_metric = METRIC_BLOCK.iloc[measure_indexes]
        measure_environment = ENVIRONMENT_BLOCK.iloc[measure_indexes]
        measure_performance = PERFORMANCE_BLOCK.iloc[measure_indexes]

        # send measure to deserialization
        midi_measure = measure(measure_metric,
                               measure_environment,
                               measure_performance,
                               SETTINGS)

        deserialized_part.insert(measure_index * int(measure_environment.TS.iloc[0][0]), midi_measure)

    deserialized_part = deserialized_part.makeNotation(inPlace=True)

    if save_as is not None:
        deserialized_part.write('midi', fp=save_as)

    return deserialized_part


def file(serialised, SETTINGS, save_as=None):
    """Deserialize a whole file"""
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    deserialized_score = music21.stream.Score()

    # get a list of unique instruments in the song
    instruments_list = list(set(serialised.index))
    instruments = [serialised.loc[i] for i in instruments_list]
    # separate song parts by instrument
    for serial in instruments:
        #   RETRIEVE BLOCKS
        #   ======||=======

        INSTRUMENT_BLOCK = pd.Series(
            {
                'NAME': serial.index[0],
                'INSTRUMENT': serial.INSTRUMENT[0],
                'MIDI_PROGRAM': serial.MIDI_PROGRAM[0],
                'SOUND': serial.SOUND[0],
            }
        )

        METRIC_BLOCK = pd.DataFrame(
            {
                'MEASURE': serial.MEASURE,
                'BEAT': serial.BEAT,
                'FRAME': serial.FRAME,
            }
        )

        ENVIRONMENT_BLOCK = pd.DataFrame(
            {
                'ORIGINAL_KS': serial.ORIGINAL_KS,
                'TS': serial.TS,
                'TEMPO': serial.TEMPO,
            }
        )

        PERFORMANCE_BLOCK = serial.iloc[:, range((len(serial.columns) - SETTINGS.KEYBOARD_SIZE), len(serial.columns))]

        part = instrument(SETTINGS,
                          INSTRUMENT_BLOCK,
                          METRIC_BLOCK.reset_index(drop=True),
                          ENVIRONMENT_BLOCK.reset_index(drop=True),
                          PERFORMANCE_BLOCK
                          )

        # insert the part at the beginning of the file
        deserialized_score.insert(0, part)

    deserialized_score.makeNotation(inPlace=True)

    # save .mid
    if deserialized_score is not None and save_as is not None:
        deserialized_score.write("midi", save_as)

    return deserialized_score

import logging
import pandas as pd
import music21
from bisect import bisect_left


def interactive_debug_serial(serialized):
    """Interactive debugger of the serialized dataframe"""
    serial_instruments = list(enumerate(set(serialized.index)))

    stop = False
    while not stop:
        print('\nInstruments detected:')
        print('\t.(ID, INSTRUMENT)')
        print('\t.---------------)')
        for instrument in serial_instruments:
            print(f'\t.{instrument}')

        sel_inst = input('\n\nEnter ID of instrument of interest: #')

        if sel_inst.upper() == '':
            break
        else:
            sel_inst = int(sel_inst)

        sel_inst_name = serial_instruments[sel_inst][1]
        target_instrument = serialized.loc[serialized.index == sel_inst_name]

        measure_view = True
        while measure_view:
            # single measure
            measure_s = input('\nEnter number of measure to show: #')
            if measure_s.upper() == '':
                measure_view = False
                stop = False
            else:
                measure_s = int(measure_s)
                measures = target_instrument[target_instrument['MEASURE'] == measure_s]
                print(measures.to_markdown())
                measure_view = True
                stop = False

# https://stackoverflow.com/questions/12141150/from-list-of-integers-get-number-closest-to-a-given-value
def take_closest(myList, myNumber):
    """
    Assumes myList is sorted. Returns closest value to myNumber.

    If two numbers are equally close, return the smallest number.

    """
    pos = bisect_left(myList, myNumber)
    if pos == 0:
        return myList[0]
    if pos == len(myList):
        return myList[-1]
    before = myList[pos - 1]
    after = myList[pos]
    if after - myNumber < myNumber - before:
        return after
    else:
        return before


def key_index2note(i, midi_offset):
    """ Receives the key index and the midi offset of the keyboard and returns a M21 Note"""
    index = i + midi_offset
    n = music21.note.Note(midi=index)
    return n


def transpose_stream_to_C(stream, force_eval=False):
    """Transpose a stream to C major, if it's in a major key, or to A minor, if it's in a minor key
    Returns a tuple in the format (key, transposed_stream)"""

    # trying to capture a M21 Key object in the stream
    stream_key = stream.getElementsByClass(music21.key.Key)
    if len(stream_key) != 0:
        stream_key = stream_key[0]
    else:
        stream_key = None

    # if we failed to get a M21 Key and 'forceEval' is set to True
    # we will try to use M21 key analyzer.
    # but this analyzer sometimes fails and breaks the code
    # so this flag should be used carefully
    if force_eval and stream_key is None:
        stream_key = stream.analyze('key')

    # if the flag jump was not taken, we raise a warn and
    # return the own input.
    # this is, we reject the input
    if stream_key is None:
        # logging.warning('Transposing measures containing empty KeySignatures can cause errors. Returning key as None '
        #                 'type.')
        return None, stream

    # copy for initialization
    transposed_stream = stream

    # at this point we should have a key
    # so it's safe to compare
    if stream_key != 'C' and stream_key != 'a':
        # transpose song to C major/A minor
        if stream_key.mode == 'major':
            transpose_int = music21.interval.Interval(stream_key.tonic, music21.pitch.Pitch('C'))
            transposed_stream = stream.transpose(transpose_int)
        elif stream_key.mode == 'minor':
            transpose_int = music21.interval.Interval(stream_key.tonic, music21.pitch.Pitch('a'))
            transposed_stream = stream.transpose(transpose_int)

    return stream_key.tonicPitchNameWithCase, transposed_stream


def measure_data(measure):
    """Receives a measure, and returns all notes from that measure in a list"""
    items = measure.flat.notes
    data = []
    for item in items:
        if isinstance(item, music21.note.Note) or isinstance(item, music21.note.Rest):
            data.append(item)
        elif isinstance(item, music21.chord.Chord):
            for p in item.pitches:
                n = music21.note.Note(pitch=p)
                n.offset = item.offset
                n.duration.quarterLength = item.duration.quarterLength
                n.volume.velocityScalar = item.volume.velocityScalar
                data.append(n)
    return data


def measure2performance(measure, SETTINGS, ts_numerator, to_bins=False):
    """Receives a measure and returns it in a multi hot encoding form"""
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    data = measure_data(measure)
    volume_flag = 1e-8
    keyboard_range = SETTINGS.KEYBOARD_SIZE + SETTINGS.KEYBOARD_OFFSET

    frames = [[False for i in range(SETTINGS.KEYBOARD_SIZE)] for j in range(ts_numerator * SETTINGS.RESOLUTION)]
    for item in data:

        # if item is a Rest, we can skip
        # since no key must be turned on
        if isinstance(item, music21.note.Rest):
            continue

        # if the item is a Note that is above
        # or below our keyboard range, we can skip
        # cause it will not be represented
        if item.pitch.midi > keyboard_range:
            continue

        # # # # # # # #
        # ITEM IS VALID
        # # # # # # # #
        #
        # here we only have
        # individual notes
        # that are inside our
        # keyboard range
        #
        # now we must discover
        # what frames must be set
        # not True at what note
        # index to get the
        # One Hot Encoding of
        # the measure

        # start and end frames
        frame_s = int(item.offset * SETTINGS.RESOLUTION)
        frame_e = int(frame_s + (item.duration.quarterLength * SETTINGS.RESOLUTION))
        # note index on our keyboard
        i_key = item.pitch.midi - SETTINGS.KEYBOARD_OFFSET
        # velocity of the note
        interval_list = [i / 128 for i in range(16, 128, 16)]
        velocity = item.volume.velocityScalar
        if to_bins:
            velocity = take_closest(interval_list, velocity)
        # if it's the first note of the bar, you don't need to check it
        if frame_s > 0:
            # if consecutive notes have the same speed, add a flag to differentiate them
            if frames[frame_s-1][i_key] == velocity:
                velocity += volume_flag
        # turn them on captain!
        for frame in range(frame_s, frame_e):
            if velocity is not None:
                # print(frame, i_key, velocity)
                frames[frame][i_key] = velocity
            else:
                # no notes
                frames[frame][i_key] = False

    # create Pandas dataframe
    note_names = [key_index2note(i, SETTINGS.KEYBOARD_OFFSET).nameWithOctave for i in range(0, SETTINGS.KEYBOARD_SIZE)]

    frame_counter = [int(i) for i in range(0, ts_numerator * SETTINGS.RESOLUTION)]
    stackframe = pd.DataFrame(frames, index=frame_counter, columns=note_names)

    return stackframe


# M21 Measure -> Pandas DataFrame
def measure(m_number, m, SETTINGS, INSTRUMENT_BLOCK, ENVIRONMENT_BLOCK, to_bins=False):
    """Serialise a single measure"""
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    # check for key changes
    m_ks, transposed_measure = transpose_stream_to_C(m, force_eval=False)
    if m_ks is None:
        m_ks = ENVIRONMENT_BLOCK.ORIGINAL_KS

    # check for tempo changes
    m_bpm = m.getElementsByClass(music21.tempo.TempoIndication)
    if len(m_bpm) != 0:
        m_bpm = m_bpm[0].getQuarterBPM()
    else:
        m_bpm = ENVIRONMENT_BLOCK.TEMPO

    m_bpm = int(m_bpm)

    # check for time sign changes
    m_ts = m.getTimeSignatures()
    if len(m_ts) != 0:
        m_ts = m_ts[0]
    else:
        m_ts = ENVIRONMENT_BLOCK.TS

    # Update Env according to this measure
    ENVIRONMENT_BLOCK.ORIGINAL_KS = m_ks
    ENVIRONMENT_BLOCK.TS = '{}/{}'.format(m_ts.numerator, m_ts.denominator)
    ENVIRONMENT_BLOCK.TEMPO = m_bpm

    #             METRIC BLOCK
    #           ======||||======
    measure_counter = [int(m_number) for i in range(SETTINGS.RESOLUTION * m_ts.numerator)]
    beat_counter = [(int(i // SETTINGS.RESOLUTION) + 1) for i in range(SETTINGS.RESOLUTION * m_ts.numerator)]
    frame_counter = [(int(i % SETTINGS.RESOLUTION) + 1) for i in range(SETTINGS.RESOLUTION * m_ts.numerator)]


    metric_bl = pd.DataFrame(
        {
            'MEASURE': measure_counter,
            'BEAT': beat_counter,
            'FRAME': frame_counter
        }
    )

    perf_bl = measure2performance(transposed_measure,
                                  SETTINGS,
                                  m_ts.numerator,
                                  to_bins)

    inst_bl = pd.concat([INSTRUMENT_BLOCK] * (m_ts.numerator * SETTINGS.RESOLUTION), axis=1).T
    env_bl = pd.concat([ENVIRONMENT_BLOCK] * (m_ts.numerator * SETTINGS.RESOLUTION), axis=1).T
    encoded_measure = pd.concat([inst_bl, metric_bl, env_bl, perf_bl], axis=1)

    return encoded_measure


# M21 Part -> Pandas DataFrame
def instrument(part, SETTINGS, part_list=None, to_bins=False):
    """Serialise a single instrument/part"""
    #
    #   INSTRUMENT BLOCK
    #

    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    # flat the stream
    part = part.semiFlat

    #   ========================
    #       DEFINING BLOCKS
    #       ===============

    #           INSTRUMENT BLOCK
    #           ======||||======
    part_name = part.partName
    inst_specs = part.getElementsByClass(music21.instrument.Instrument)[0]
    m21_inst = part.getElementsByClass(music21.instrument.Instrument)[-1]
    inst_name = m21_inst.instrumentName

    # This is a terminal case.
    # Without the instrument name a lot of problems show up.
    # So, we will avoid this case for now
    if inst_name is None:
        return None

    inst_sound = inst_specs.instrumentSound

    # to avoid the problem of having parts with the same name
    while part_name in part_list:
        part_name += "'"
    part_list.append(part_name)

    try:
        midi_program = m21_inst.midiProgram
    except:
        midi_program = 0
        logging.warning('Could not retrieve Midi Program from instrument, setting it to default value 0 ({})'
                        .format(music21.instrument.instrumentFromMidiProgram(midi_program).instrumentName))

    INSTRUMENT_BLOCK = pd.Series(
        {
            'NAME': part_name,
            'INSTRUMENT': inst_name,
            'MIDI_PROGRAM': midi_program,
            'SOUND': inst_sound
        }
    )
    #
    #           ENVIRONMENT BLOCK
    #            ======||||======

    # get part tempo
    metronome = part.getElementsByClass(music21.tempo.TempoIndication)
    if len(metronome) == 0:
        bpm = 120
        logging.warning('Could not retrieve Metronome object from Part, setting BPM to default value ({})'
                        .format(bpm))
    else:
        bpm = metronome[0].getQuarterBPM()
    bpm = int(bpm)

    # filter parts that are not in 4/4
    time_signature = part.getElementsByClass(music21.meter.TimeSignature)
    if len(time_signature) == 0:
        ts = music21.meter.TimeSignature('4/4')
        logging.warning('Could not retrieve Time Signature object from Part, setting TS to default value ({})'
                        .format(ts))
    else:
        ts = time_signature[0]

    # transpose song to C major/A minor
    original_ks, transposed_part = transpose_stream_to_C(part, force_eval=True)

    n_measures = len(part) + 1

    ENVIRONMENT_BLOCK = pd.Series(
        {
            'ORIGINAL_KS': original_ks,
            'TS': '{}/{}'.format(ts.numerator, ts.denominator),
            'TEMPO': bpm
        }
    )

    # a vector containing the measures
    part_df = []
    first_measure = True
    for i, m in enumerate(transposed_part.measures(1, n_measures)):

        serialised_measure = pd.DataFrame(
            measure(i+1, m,
                    SETTINGS,
                    INSTRUMENT_BLOCK,
                    ENVIRONMENT_BLOCK,
                    to_bins
                    )
        )

        if first_measure:
            part_df = serialised_measure
            first_measure = False
        else:
            part_df = pd.concat([part_df, serialised_measure], axis=0, ignore_index=True)

        part_df.index = part_df.index + 1

    return part_df


# MIDI -> Interpretation (Pandas DataFrame)
def file(path, SETTINGS, save_as=None, to_bins=False):
    """Serialise a .mid file"""
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    score = music21.converter.parse(path)
    score = score.makeNotation()
    score = score.expandRepeats()

    part_list = []
    serialised_parts = []

    for part in score.parts:
        serialised_parts.append(
            instrument(part,
                       SETTINGS,
                       part_list,
                       to_bins)
        )

    serialised_df = pd.concat([*serialised_parts], axis=0)
    serialised_df = serialised_df.set_index('NAME')

    if save_as is not None:
        serialised_df.to_pickle(save_as)

    return serialised_df

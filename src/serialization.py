import logging
import os
import time
import pandas as pd
import numpy as np
import music21
from pathlib import Path
from . import key_index2note, transpose_stream_to_C
# open and read file
#
# MIDI -> M21 Score
def open_file(midi_path, no_drums=True):
    # declare and read
    mf = music21.midi.MidiFile()
    mf.open(midi_path)

    # score = music21.converter.parse(midi_path).makeNotation().voicesToParts()

    if mf.format not in [0, 1]:
        # m21 cant read
        logging.warning('Music21 cant open format {} MIDI files. Skipping.'.format(mf.format))
        return None

    mf.read()
    mf.close()

    # if no_drums is on, we'll remove the drums
    if no_drums:
        for i in range(0, len(mf.tracks)):
            mf.tracks[i].events = [ev for ev in mf.tracks[i].events if ev.channel != 10]

    score = music21.midi.translate.midiFileToStream(mf)
    score = score.makeNotation()
    score = score.voicesToParts()

    return score


# get all notes from m21 obj
def measure_data(measure):
    items = measure.flat.notes
    data = []
    for item in items:
        if isinstance(item, music21.note.Note) or isinstance(item, music21.note.Rest):
            data.append(item)
            # print('data', data)
        elif isinstance(item, music21.chord.Chord):
            for p in item.pitches:
                n = music21.note.Note(pitch=p)
                n.offset = item.offset
                n.duration.quarterLength = item.duration.quarterLength
                n.volume.velocityScalar = item.volume.velocityScalar
                data.append(n)
                # print('data', data)

    return data


# extract frames from measure
#
#  M21 Measure -> Multi Hot Encoding
def measure2performance(measure, SETTINGS, ts_numerator):
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    data = measure_data(measure)
    # for n in data:
    #     print(n, n.offset, n.duration.quarterLength, end=', ')
    # print()
    # print(len(data))
    keyboard_range = SETTINGS.KEYBOARD_SIZE + SETTINGS.KEYBOARD_OFFSET

    frames = [[0 for i in range(SETTINGS.KEYBOARD_SIZE)] for j in range(ts_numerator * SETTINGS.RESOLUTION)]
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
        # print(f'{frame_s}/{frame_e}')
        # if frame_s == 56:
        #     print(item.offset, item.pitch, item.duration.quarterLength)
        # note index on our keyboard
        i_key = item.pitch.midi - SETTINGS.KEYBOARD_OFFSET
        velocity = item.volume.velocityScalar
        # turn them on captain!
        for frame in range(frame_s, frame_e):
            # print(f'{frame}/{frame_e}')
            # input()
            if velocity is not None:
                frames[frame][i_key] = velocity
                # if frame == frame_s:
                #     # first frame, play
                #     frames[frame][i_key] = (True, velocity)
                #     # print(frames[frame][i_key])
                #     # input()
                # elif frame == frame_e-1:
                #     # last frame, stop
                #     frames[frame][i_key] = (False, velocity)
                #     # print(frames[frame][i_key])
                #     # input()
                # else:
                #     # none, continue
                #     frames[frame][i_key] = velocity
                #     # print(frames[frame][i_key])
            else:
                # no notes
                # print(item.pitch, item.offset)
                frames[frame][i_key] = 0

    # create Pandas dataframe
    note_names = [key_index2note(i, SETTINGS.KEYBOARD_OFFSET).nameWithOctave for i in range(0, SETTINGS.KEYBOARD_SIZE)]

    frame_counter = [int(i) for i in range(0, ts_numerator * SETTINGS.RESOLUTION)]
    stackframe = pd.DataFrame(frames, index=frame_counter, columns=note_names)

    return stackframe


# Serialise a single measure
#
# M21 Measure -> Pandas DataFrame
def measure(m_number, m, SETTINGS, INSTRUMENT_BLOCK, ENVIRONMENT_BLOCK):
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    # TODO: ligadura, conectar duas measures e somar as durações

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
        # if m_ts != ENVIRONMENT_BLOCK.TS:
        #     # ts changed
        #     if m_ts.ratioString != '4/4':
        #         logging.warning('Found measure not in 4/4, skipping.')
        #         return None
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

    # print(len(measure_counter), len(beat_counter), len(frame_counter))

    metric_bl = pd.DataFrame(
        {
            'MEASURE': measure_counter,
            'BEAT': beat_counter,
            'FRAME': frame_counter
        }
    )

    perf_bl = measure2performance(transposed_measure,
                                  SETTINGS,
                                  m_ts.numerator)

    inst_bl = pd.concat([INSTRUMENT_BLOCK] * (m_ts.numerator * SETTINGS.RESOLUTION), axis=1).T

    env_bl = pd.concat([ENVIRONMENT_BLOCK] * (m_ts.numerator * SETTINGS.RESOLUTION), axis=1).T
    # env_df = env_df.reshape(len(ENVIRONMENT_BLOCK), SETTINGS.RESOLUTION)

    # print(f'INST DF: \n\n {inst_df.to_string()} \n Shape {inst_df.shape}\n')
    # print(f'ENV DF: \n\n {env_df.to_string()} \n Shape {env_df.shape}\n')
    # print(f'PERFORMANCE DF: \n\n {stackframe.to_string()} \n Shape {stackframe.shape}\n')

    encoded_measure = pd.concat([inst_bl, metric_bl, env_bl, perf_bl], axis=1)

    return encoded_measure


# Serialise a single instrument/part
#
# M21 Part -> Pandas DataFrame
def instrument(part, SETTINGS, instrument_list=None):
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
    m21_inst = part.getElementsByClass(music21.instrument.Instrument)[0]
    inst_name = m21_inst.instrumentName

    # This is a terminal case.
    #
    # Without the instrument name a lot of problems show up.
    # So, we will avoid this case for now
    if inst_name is None:
        return None

    inst_sound = m21_inst.instrumentSound
    instrument_list.append(inst_name)

    try:
        midi_program = m21_inst.midiProgram
    except:
        midi_program = 0
        logging.warning('Could not retrieve Midi Program from instrument, setting it to default value 0 ({})'
                        .format(music21.instrument.instrumentFromMidiProgram(midi_program).instrumentName))

    print(f'\n====================',
          f'\nPart name: {part_name}',
          f'\nPart instrument name: {inst_name}',
          f'\nPart instrument MIDI program: {midi_program}',
          f'\nInstrument sound: {inst_sound}')

    INSTRUMENT_BLOCK = pd.Series(
        {
            'NAME': part_name,
            'INSTRUMENT': inst_name,
            'MIDI_PROGRAM': midi_program,
            'SOUND': inst_sound
        }
    )

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
    # original_ks, transposed_part = transpose_stream_to_C(part, force_eval=False)
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
                    ENVIRONMENT_BLOCK
                    )
        )

        if first_measure:
            part_df = serialised_measure
            first_measure = False
        else:
            part_df = pd.concat([part_df, serialised_measure], axis=0, ignore_index=True)

        part_df.index = part_df.index + 1

    return part_df


# Serialise a .mid file
#
# MIDI -> Interpretation (Pandas DataFrame)

def file(path, SETTINGS, save_as=None):
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    # score = open_file(path)
    score = music21.converter.parse(path)
    # score.show("text")
    print(f'Is well formed score? {score.isWellFormedNotation()}')
    score = score.makeNotation()
    score = score.expandRepeats()

    # score = music21.instrument.unbundleInstruments(score)
    # score.show('text')
    # input()

    # meta = score.metadata
    instrument_list = []

    # score.show('text')
    # input()

    parts_in_score = music21.instrument.partitionByInstrument(score).parts
    # parts_in_score = score.parts

    # print('Instruments in file: {}'.format(len(score.parts)))
    # input()

    serialised_parts = []

    # for part in parts_in_score:
    for part in score.parts:
        serialised_parts.append(
            instrument(part,
                       SETTINGS,
                       instrument_list)
        )

    serialised_df = pd.concat([*serialised_parts], axis=0)
    serialised_df = serialised_df.set_index('NAME')

    if save_as is not None:
        serialised_df.to_pickle(save_as)

    return serialised_df

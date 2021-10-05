from pathlib import Path
import logging
import os
import time
import numpy as np
from tqdm import tqdm
import pandas as pd
import music21
from . import key_index2note, get_transpose_interval_from_C

#   Deserialise a single measure
#
#   Multi Hot Encoding (Pandas DataFrame) -> M21
#
# TODO: ligadura, conectar duas measures e somar as durações
def measure(m_metric, m_environment, m_performance, SETTINGS):
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
    # print(met_perf_concat); input()

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
        # print(f'\nMeasure note\n============\n', measure_note)

        # filter the frames where the current note is on
        on_frames = met_perf_concat.loc[met_perf_concat.loc[:, measure_note] != False, measure_note]
        # on_frames.index += 1
        # print(f'\nOn frames\n============\n', on_frames)

        if not on_frames.empty:

            # print(f'\nOn frames\n============\n', on_frames)

            '''
            On frames
            ============
             8      (True, 0.5039370078740157)
            9                        0.503937
            10    (False, 0.5039370078740157)
            28     (True, 0.5039370078740157)
            29                       0.503937
            30    (False, 0.5039370078740157)
            Name: A4, dtype: object
            '''

            frames_indexes = on_frames.index

            # TODO: maybe we should set a threshold on what should become another note
            # For example: if there's just one OFF frame between two ON frames, the OFF frame would be ignored

            # declare note object
            note_obj = music21.note.Note(nameWithOctave=measure_note)

            this_note_on_frames = []

            # iterate over frames
            for i_on_frame, current_frame in enumerate(on_frames):

                frame_number = frames_indexes[i_on_frame]

                # print(f'\nFrame {frame_number}\n=============\n', current_frame); input()

                this_note_on_frames.append(frame_number)
                # AQUI VAI SER A DIVISAO PELO TIPO DO DADO

                if i_on_frame == len(on_frames)-1:
                    # play note
                    # if current_frame[0]:
                        # note start
                    this_note_on_frames.append(frame_number)
                    # note end
                    beat_dur = len(this_note_on_frames) / SETTINGS.RESOLUTION
                    note_obj.duration.quarterLength = abs(beat_dur)
                    # get the start frame of the note
                    beat_offset = (this_note_on_frames[0] / SETTINGS.RESOLUTION)
                    # insert into measure
                    deserialized_measure.insert(beat_offset, note_obj)
                    this_note_on_frames = []
    # transpose it back to the original ks
    deserialized_measure.transpose(transpose_int, inPlace=True)

    # insert rests in between the notes
    deserialized_measure.makeRests(fillGaps=False, inPlace=True)

    # make offsets and durations more strict
    # NOTE: it can remove the 'humanity' of the dynamics
    # deserialized_measure.quantize(inPlace=True)

    # return it
    return deserialized_measure



# deserialize a instrument line
def instrument(SETTINGS, INSTRUMENT_BLOCK, METRIC_BLOCK, ENVIRONMENT_BLOCK, PERFORMANCE_BLOCK, save_as=None):
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    # M21 object to be returned
    deserialised_part = music21.stream.Part()

    part_name = INSTRUMENT_BLOCK.NAME
    inst_name = INSTRUMENT_BLOCK.INSTRUMENT
    midi_program = INSTRUMENT_BLOCK.MIDI_PROGRAM
    inst_sound = INSTRUMENT_BLOCK.SOUND

    # print(f'\n====================',
    #       f'\nPart name: {part_name}',
    #       f'\nInstrument name: {inst_name}',
    #       f'\nInstrument MIDI program: {midi_program}',
    #       f'\nInstrument sound: {inst_sound}')

    # set instrument
    try:
        m21_inst = music21.instrument.fromString(inst_name)
    except:
        m21_inst = music21.instrument.instrumentFromMidiProgram(midi_program)

    # m21_inst.instrumentSound = inst_sound

    # print(f'\nMusic21 Instrument: {type(m21_inst)}',
    #       f'\nInstrument sound: {m21_inst.instrumentSound}')
    # inst.autoAssignMidiChannel()
    deserialised_part.insert(0, m21_inst)

    # total number of measures (bars)
    # in this part
    n_measures = max(set(METRIC_BLOCK.MEASURE))

    # deserialize measures
    #
    # iterate over measures (bars)
    for measure_index in range(1, n_measures + 1):
        # print(f'Measure {measure_index}')

        measure_indexes = METRIC_BLOCK.loc[METRIC_BLOCK['MEASURE'] == measure_index]
        measure_indexes = measure_indexes.index

        measure_metric = METRIC_BLOCK.iloc[measure_indexes]
        measure_environment = ENVIRONMENT_BLOCK.iloc[measure_indexes]
        measure_performance = PERFORMANCE_BLOCK.iloc[measure_indexes]

        # print(f'Measure {measure_index}'.

        # send measure to deserialization
        midi_measure = measure(measure_metric,
                               measure_environment,
                               measure_performance,
                               SETTINGS)

        deserialised_part.insert(measure_index * int(measure_environment.TS.iloc[0][0]), midi_measure)

    deserialised_part = deserialised_part.makeNotation(inPlace=True)

    if save_as is not None:
        deserialised_part.write('midi', fp=save_as)

    return deserialised_part


# deserialize a whole file
def file(serialised, SETTINGS, save_as=None):
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    deserialized_score = music21.stream.Score()

    # get a list of unique instruments in the song
    instruments_list = list(set(serialised.index))
    instruments = [serialised.loc[i] for i in instruments_list]

    # print(f'\n\nINSTRUMENTS\n===========\n {instruments}'); input()

    # separate song parts by instrument
    for serial in instruments:
        #   RETRIEVE BLOCKS
        #   ======||=======

        # print(f'\nSERIAL\n===========\n {serial}'); input()

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

        # print(PERFORMANCE_BLOCK)

        # print('Decoding instrument: {}'.format(INSTRUMENT_BLOCK.NAME))

        part = instrument(SETTINGS,
                          INSTRUMENT_BLOCK,
                          METRIC_BLOCK.reset_index(drop=True),
                          ENVIRONMENT_BLOCK.reset_index(drop=True),
                          PERFORMANCE_BLOCK
                          )

        # insert the part at the beginning of the file
        deserialized_score.insert(0, part)
        # print(instruments)
        # input()
        # deserialized_score = deserialized_score.makeVoices(inPlace=True)
        # deserialised_part = deserialised_part.partsToVoices()
    # deserialized_score = music21.instrument.unbundleInstruments(deserialized_score)
    deserialized_score.makeNotation(inPlace=True)

    # save .mid
    if deserialized_score is not None and save_as is not None:
        deserialized_score.write("midi", save_as)

    return deserialized_score

from pathlib import Path
import logging
import os
import time
import numpy as np
from tqdm import tqdm
import pandas as pd
import music21


# discover if a list is a continuous sequence
def is_continuous(l):
    # print(f'list: {list}')
    # input()
    # if list is empty or len is 1,  return True
    if len(l) < 2: return True
    return sorted(l) == list(range(min(l), max(l) + 1))


# Key index in our keyboard -> M21 Note
def key_index2note(i, midi_offset):
    index = i + midi_offset
    n = music21.note.Note(midi=index)
    return n


def get_transpose_interval(ks):
    if ks is None:
        return None

    if ks != 'C' and ks != 'a':
        if ks.mode == 'major':
            return music21.interval.Interval(music21.pitch.Pitch('C'), ks.tonic)
        elif ks.mode == 'minor':
            return music21.interval.Interval(music21.pitch.Pitch('a'), ks.tonic)


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
    measure_ks = m_environment.KS.mode()[0]
    measure_ts = m_environment.TS.mode()[0]
    measure_tempo = m_environment.TEMPO.mode()[0]

    ks = music21.key.Key(measure_ks)
    transpose_int = get_transpose_interval(ks)
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
        on_frames = m_performance.loc[m_performance.loc[:, measure_note] != False, measure_note]

        if not on_frames.empty:

            # print(f'On frames: {on_frames}')
            # input()

            # get the list of on frames
            frames = list(m_metric.loc[on_frames.index].FRAME)
            # frames = range(1, len(frames) + 1)

            # print(f'Frames: {frames}')
            # input()

            # if 'frames' is a continuous sequence it can become a single note.
            # if not, it'll become more than one

            # TODO: maybe we should set a threshold on what should become another note
            # For example: if there's just one OFF frame between two ON frames, the OFF frame would be ignored

            temp = []
            while not is_continuous(frames):
                # print('a')
                # this will keep track of the frames we
                # have already counted
                while is_continuous(temp):
                    # print('b')
                    # temp is continuous, we'll try to add
                    # the next frame
                    temp.append(frames[0])

                    if is_continuous(temp):
                        # it temp is still continuous, it's safe to
                        # remove the frame added in the last line
                        # from the original 'frames' list
                        del frames[0]
                    else:
                        # if temp is now no more
                        # a continuous sequence, we must
                        # remove from 'temp' the frame that
                        # caused this property loss
                        del temp[-1]



                # # calculate duration in frames (amount of frames on)
                # n_obj = music21.note.Note(nameWithOctave=measure_note)
                # beat_dur = len(temp) / SETTINGS.RESOLUTION  # amount of beats
                # n_obj.duration.quarterLength = abs(beat_dur)
                # print(on_frames.loc[measure_note])
                # input()
                # # n_obj.volume.velocityScalar = on_frames[]
                #
                # # get the start frame of the note
                # beat_offset = (frames[0] * SETTINGS.RESOLUTION) / ts.numerator
                #
                # # insert into stream
                # deserialized_measure.insert(beat_offset, n_obj)

            #
            #  here list of frames is a continuous sequence
            #

            # calculate duration in quarters
            note_obj = music21.note.Note(nameWithOctave=measure_note)
            beat_dur = len(frames) / SETTINGS.RESOLUTION
            note_obj.duration.quarterLength = abs(beat_dur)

            # print(f'Metric at frames index: {m_metric.loc[frames.index]}')

            # get the start frame of the note
            beat_offset = (frames[0] * SETTINGS.RESOLUTION) % ts.numerator
            # beat_offset = (min(m_metric.iloc[frames.index].BEAT) + (min(m_metric.iloc[frames.index].FRAME) / SETTINGS.RESOLUTION))
            # print(f'Beat Offset: {beat_offset}')
            # input()

            # insert into measure
            deserialized_measure.insert(beat_offset, note_obj)

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

    part_name = INSTRUMENT_BLOCK.NAME[0]
    inst_name = INSTRUMENT_BLOCK.INSTRUMENT[0]
    midi_program = INSTRUMENT_BLOCK.MIDI_PROGRAM[0]

    print(f'\n====================',
          f'\nPart name: {part_name}',
          f'\nInstrument name: {inst_name}',
          f'\nInstrument MIDI program: {midi_program}')

    # set instrument
    try:
        m21_inst = music21.instrument.instrumentFromMidiProgram(midi_program)
    except:
        m21_inst = music21.instrument.fromString(inst_name)

    print(f'\nMusic21 Instrument: {type(m21_inst)}',
          f'\nInstrument sound: {m21_inst.instrumentSound}')
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

        print(f'Measure {measure_index}')

        # send measure to deserialization
        midi_measure = measure(measure_metric,
                               measure_environment,
                               measure_performance,
                               SETTINGS)

        deserialised_part.insert(measure_index, midi_measure)

    deserialised_part = deserialised_part.makeNotation(inPlace=True)

    if save_as is not None:
        deserialised_part.write('midi', fp=save_as)

    return deserialised_part


# deserialize a whole file
def file(serialised, SETTINGS, save_as=None):
    if not isinstance(SETTINGS, pd.Series):
        SETTINGS = pd.Series(SETTINGS)

    deserialized_score = music21.stream.Score()

    # meta = serialised.metadata

    # get a list of unique instruments in the song
    instruments_list = list(set(serialised.index))
    instruments = [serialised.loc[i] for i in instruments_list]

    # separate song parts by instrument
    for serial in instruments:
        #   RETRIEVE BLOCKS
        #   ======||=======

        INSTRUMENT_BLOCK = pd.DataFrame(
            {
                'INSTRUMENT': serial.index,
                'NAME': serial.NAME,
                'MIDI_PROGRAM': serial.MIDI_PROGRAM
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
                'KS': serial.KS,
                'TS': serial.TS,
                'TEMPO': serial.TEMPO,
            }
        )

        # drop blocks to get performance
        drop_list = [i for i in set(INSTRUMENT_BLOCK.columns)]
        drop_list.remove('INSTRUMENT')
        drop_list = drop_list + [i for i in set(METRIC_BLOCK.columns)]
        drop_list = drop_list + [i for i in set(ENVIRONMENT_BLOCK.columns)]
        PERFORMANCE_BLOCK = serial.drop(columns=drop_list).reset_index(drop=True)

        # print(PERFORMANCE_BLOCK)

        # print('Decoding instrument: {}'.format(INSTRUMENT_BLOCK.NAME))

        part = instrument(SETTINGS,
                          INSTRUMENT_BLOCK,
                          METRIC_BLOCK.reset_index(drop=True),
                          ENVIRONMENT_BLOCK.reset_index(drop=True),
                          PERFORMANCE_BLOCK.reset_index(drop=True)
                          )

        # insert the part at the beginning of the file
        deserialized_score.insert(0, part)
        # print(instruments)
        # input()
        deserialized_score = deserialized_score.makeVoices(inPlace=True)
        # deserialised_part = deserialised_part.partsToVoices()
        # deserialized_score.makeNotation(inPlace=True)

    # save .mid
    if save_as is not None:
        deserialized_score.write("midi", save_as)

    return deserialized_score

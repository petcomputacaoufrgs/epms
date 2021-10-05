from music21 import interval, pitch, key, note
import more_itertools as mit

def get_continuos(on_frames):
    return [list(group) for group in mit.consecutive_groups(on_frames)]


# Key index in our keyboard -> M21 Note
def key_index2note(i, midi_offset):
    index = i + midi_offset
    n = note.Note(midi=index)
    return n


# return tuple (key, transposed_stream)
#
# (label, key)
def transpose_stream_to_C(stream, force_eval=False):
    # trying to capture a M21 Key object in the stream
    stream_key = stream.getElementsByClass(key.Key)
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
            transpose_int = interval.Interval(stream_key.tonic, pitch.Pitch('C'))
            transposed_stream = stream.transpose(transpose_int)
        elif stream_key.mode == 'minor':
            transpose_int = interval.Interval(stream_key.tonic, pitch.Pitch('a'))
            transposed_stream = stream.transpose(transpose_int)

    return stream_key.tonicPitchNameWithCase, transposed_stream


def get_transpose_interval_from_C(ks):
    if ks is None:
        return None

    if ks != 'C' and ks != 'a':
        if ks.mode == 'major':
            return interval.Interval(pitch.Pitch('C'), ks.tonic)
        elif ks.mode == 'minor':
            return interval.Interval(pitch.Pitch('a'), ks.tonic)


def interactive_debug_serial(serialized):
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
                measure_view = False; stop = False;
            else:
                measure_s = int(measure_s)

                # measure_e = measure_s
                # measures = target_instrument[target_instrument['MEASURE'].between(measure_s, measure_e, inclusive=True)]
                measures = target_instrument[target_instrument['MEASURE'] == measure_s]
                print(measures.to_markdown())
                measure_view = True
                stop = False

        # print(f'Serial of instrument {sel_inst_name}:\n ', target_instrument.to_string())

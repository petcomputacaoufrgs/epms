from music21 import interval, pitch, key, note
from bisect import bisect_left

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


def key_index2note(i, midi_offset):
    """ Receives the key index and the midi offset of the keyboard and returns a M21 Note"""
    index = i + midi_offset
    n = note.Note(midi=index)
    return n


def transpose_stream_to_C(stream, force_eval=False):
    """Transpose a stream to C major, if it's in a major key, or to A minor, if it's in a minor key
    Returns a tuple in the format (key, transposed_stream)"""

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

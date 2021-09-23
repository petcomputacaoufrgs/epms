import pandas as pd
from music21 import converter, environment
import tabulate
from ems import serialization, deserialization

environment.set('musicxmlPath', '/usr/bin/mscore')

SETTINGS = {
    'RESOLUTION': 16,
    'KEYBOARD_SIZE': 88,
    'KEYBOARD_OFFSET': 21
}

#        -> ERROR ON WRITE BACK! <-
#           =========-=========
# Deserializing...
# Traceback (most recent call last):
#   File "/***/Projects/EMS/test_sample.py", line 48, in <module>
#     deserialised = deserialisation.file(serialised,
#   File "/***/Projects/EMS/ems/deserialization.py", line 272, in file
#     deserialised_score.write("midi", save_as)
#   File "/***/.local/lib/python3.9/site-packages/music21/stream/__init__.py", line 253, in write
#     return super().write(fmt=fmt, fp=fp, **keywords)
#   File "/***/.local/lib/python3.9/site-packages/music21/base.py", line 2552, in write
#     return formatWriter.write(self,
#   File "/***/.local/lib/python3.9/site-packages/music21/converter/subConverters.py", line 1064, in write
#     mf = midiTranslate.music21ObjectToMidiFile(obj, **midiTranslateKeywords)
#   File "/***/.local/lib/python3.9/site-packages/music21/midi/translate.py", line 254, in music21ObjectToMidiFile
#     return streamToMidiFile(music21Object, addStartDelay=addStartDelay)
#   File "/***/.local/lib/python3.9/site-packages/music21/midi/translate.py", line 2364, in streamToMidiFile
#     midiTracks = streamHierarchyToMidiTracks(s, addStartDelay=addStartDelay)
#   File "/***/.local/lib/python3.9/site-packages/music21/midi/translate.py", line 2244, in streamHierarchyToMidiTracks
#     updatePacketStorageWithChannelInfo(packetStorage, channelByInstrument)
#   File "/***/.local/lib/python3.9/site-packages/music21/midi/translate.py", line 2187, in updatePacketStorageWithChannelInfo
#     initCh = channelByInstrument[instObj.midiProgram]
# KeyError: XX


#   TEST FILES SUCCESS STATUS:
#       ==============
# . Hallelujah (ver 3 by Zagajewski).mid -> KeyError: 52
# .Do It Again.mid                       -> KeyError: 80
# .Hey Nineteen.mid                      -> KeyError: 52
# .Killer Queen                          -> KeyError: 52
# .Deacon Blues.mid                      -> KeyError:


file = 'test_files/Lucy In The Sky With Diamonds.mid'
out_serialized_name = 'out_serial.pkl'
out_deserialized_name = 'out_deserialised.mid'


# Show original file as text
# original = converter.parse(file).makeNotation().voicesToParts()
# original.plot()
# original.show()
# input()

# Serialize data
print('Serializing...')
serialized = serialization.file(file,
                                SETTINGS,
                                save_as=out_serialized_name)

# print('Getting serial...')
# serialized = pd.read_pickle(out_serialized_name)

# print(serialized.to_string())
# input()

serial_instruments = list(enumerate(set(serialized.index)))

# stop = False
# while not stop:
#     print('\nInstruments detected:')
#     print('\t.(ID, INSTRUMENT)')
#     print('\t.---------------)')
#     for instrument in serial_instruments:
#         print(f'\t.{instrument}')
#
#     sel_inst = input('\n\nEnter ID of instrument of interest or STOP: #')
#
#     if sel_inst.upper() == 'STOP': break
#     else: sel_inst = int(sel_inst)
#
#     sel_inst_name = serial_instruments[sel_inst][1]
#
#     target_instrument = serialized.loc[serialized.index == sel_inst_name]
#
#     print(f'Serial of instrument {sel_inst_name}:\n ', target_instrument.to_string())
#
#     measure_s = 5
#     measure_e = 8
#     measures = target_instrument[target_instrument['MEASURE'].between(measure_s, measure_e, inclusive=True)]
#     print(measures.to_markdown())

# Deserialize data
print('\n\n\n\t << Deserializing... >> \n\n')
deserialized = deserialization.file(serialized,
                                    SETTINGS,
                                    save_as=out_deserialized_name)

# deserialised.plot()
# deserialized.show('midi')

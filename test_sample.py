import music21.chord
import pandas as pd
from music21 import converter, environment
import tabulate
from src import serialization, deserialization, interactive_debug_serial

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
# .Deacon Blues.mid                      -> KeyError: 52


song_name = "Youre beautiful.mid"
file = 'test_midi_files/' + song_name
out_serialized_name = 'temp_files/serial.pkl'
out_deserialized_name = 'temp_files/result_agrvai' + song_name

# Show original file as text
# original = converter.parse(file).makeNotation().voicesToParts()
# n = serialization.measure_data(original)
# for n1 in n:
#     print(n.offset)
# original.plot()
# original.show()
# original.show("text")
# input()

# Serialize data
print('Serializing...')
serialized = serialization.file(file,
                                SETTINGS,
                                save_as=out_serialized_name)
# print(serialized.head(64).to_markdown())
# print(serialized.loc[serialized["MEASURE"] == 24].to_markdown())
# print(serialized.loc[serialized["MEASURE"] == 25].to_markdown())
# print(serialized.loc[serialized["MEASURE"] == 26].to_markdown())
# print(serialized.loc[serialized["MEASURE"] == 27].to_markdown())
# print('Getting serial...')
# serialized = pd.read_pickle(out_serialized_name)
# print(serialized.to_string())

# interactive_debug_serial(serialized)

# Deserialize data
print('\n\n\n\t << Deserializing... >> \n\n')
deserialized = deserialization.file(serialized,
                                    SETTINGS,
                                    save_as=out_deserialized_name)

deserialized.show('text')
# deserialized.plot()
# input()

# deserialized.plot()
# deserialized.show('midi')

import pandas as pd
from music21 import converter, environment
import tabulate
from ems import serialisation, deserialisation

environment.set('musicxmlPath', '/usr/bin/mscore')

SETTINGS = {
    'RESOLUTION': 16,
    'KEYBOARD_SIZE': 88,
    'KEYBOARD_OFFSET': 21
}

#        -> ERROR ON WRITE BACK! <-
#           =========-=========
# Deserialising...
# Traceback (most recent call last):
#   File "/***/Projects/EMS/test_sample.py", line 48, in <module>
#     deserialised = deserialisation.file(serialised,
#   File "/***/Projects/EMS/ems/deserialisation.py", line 272, in file
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

file = 'test_files/Aguas De Marco.mid'
out_serialised_name = 'out_serial.pkl'
out_deserialised_name = 'out_deserialised.mid'


# Show original file as text
original = converter.parse(file).makeNotation().voicesToParts()
# original.plot()
# original.show()
# input()

# Serialise data
print('Serialising...')
# serialised = serialisation.file(file,
#                                 SETTINGS,
#                                 save_as=out_serialised_name)
serialised = pd.read_pickle(out_serialised_name)


instruments_in_file = list(set(serialised.index))
print(instruments_in_file)

# target_instrument = serialised[serialised.index == instruments_in_file[0]]

# print(serialised[:64*2].to_string())
# print(serialised.head(50).to_markdown())
# print(target_instrument[:96].to_markdown())
# input()

# Deserialise data
print('Deserialising...')
deserialised = deserialisation.file(serialised,
                                    SETTINGS,
                                    save_as=out_deserialised_name)

# deserialised.plot()
# deserialised.show('midi')

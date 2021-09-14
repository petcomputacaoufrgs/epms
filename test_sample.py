from music21 import converter
import tabulate
from ems import serialisation, deserialisation

SETTINGS = {
    'RESOLUTION': 96,
    'KEYBOARD_SIZE': 88,
    'KEYBOARD_OFFSET': 21
}

file = 'test_files/Aint No Sunshine.mid'
out_serialised_name = 'out_serial.pkl'
out_deserialised_name = 'out_deserialised.mid'


# Show original file as text
original = converter.parse(file).makeNotation().voicesToParts()
# original.plot()
# original.show('text')
# input()

# Serialise data
print('Serialising...')
serialised = serialisation.file(file,
                                SETTINGS,
                                save_as=out_serialised_name)

# print(serialised)
print(serialised.head(10).to_markdown())
# input()

# Deserialise data
print('Deserialising...')
deserialised = deserialisation.file(serialised,
                                    SETTINGS,
                                    save_as=out_deserialised_name)

deserialised.plot()
deserialised.show('text')

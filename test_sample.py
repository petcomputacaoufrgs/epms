from src import serialization, deserialization


SETTINGS = {
    'RESOLUTION': 16,
    'KEYBOARD_SIZE': 88,
    'KEYBOARD_OFFSET': 21
}


song_name = "Aguas de Marco"
file = 'test_midi_files/' + song_name + ".mid"
out_serialized_name = "../resultFinal/pkl/" + song_name + ".pkl"
out_deserialized_name = '../temp_files/result_fixinst/' + song_name + "_to_bins.mid"

# Show original file as text
# original = converter.parse(file).makeNotation()
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
                                # out_serialized_name,
                                to_bins=True)



print(serialized.head(64).to_markdown())

# Deserialize data
print('Deserializing...')
deserialized = deserialization.file(serialized,
                                    SETTINGS,
                                    save_as=out_deserialized_name)
# deserialized.show("midi")
# deserialized.plot()


#
# logic taken from https://github.com/tonylukasavage/lucid-dream and ported to python :)
#

import struct
import math

import h5py

import numpy as np


def get_attribute_names(element):
    attr = {}
    for key, value in element.items():
        if (key.find('_') != 0 and value != None):
            attr[key] = value

    return attr


class Encoder():
    ranges = [
        {"type": 'uint8', "range": [0, 255]},
        {"type": 'int16', "range": [-32768, 32767]},
        {"type": 'int32', "range": [-2147483648, 2147483647]}
    ]

    def __init__(self, writer):
        self.f = writer

    def populate_encode_key_names(self, d, seen):
        name = d["__name"]

        try:
            seen[name] = seen[name] + 1
        except KeyError:
            seen[name] = 1

        try:
            children = d["__children"]
        except KeyError:
            children = []

        for key, value in d.items():
            if (key.find('__') != 0):
                try:
                    seen[key] = seen[key] + 1
                except KeyError:
                    seen[key] = 1

            if (isinstance(value, str) and key != 'innerText'):
                try:
                    seen[value] = seen[value] + 1
                except KeyError:
                    seen[value] = 1

        for child in children:
            self.populate_encode_key_names(child, seen)

    def encode_element(self, element, lookup):
        if (isinstance(element, list)):
            for el in element:
                self.encode_element(el, lookup)
        else:
            attrs = get_attribute_names(element)

            try:
                children = element["__children"]
            except KeyError:
                children = []

            try:
                self.f.write(lookup[element["__name"]], "uint16")
            except KeyError:
                self.f.write(0, "uint16")

            self.f.write(len(attrs.keys()), "uint8")

            for key, value in attrs.items():
                try:
                    self.f.write(lookup[key], "uint16")
                except KeyError:
                    self.f.write(0, "uint16")

                self.encode_value(key, value, lookup)

            self.f.write(len(children), "uint16")
            self.encode_element(children, lookup)

    def encode_value(self, attr, value, lookup):
        if(isinstance(value, float)):
            self.f.write(4, "uint8")
            self.f.write(value, "float")

        elif(isinstance(value, int) and not isinstance(value, bool)):
            for i in range(0, len(Encoder.ranges)):
                type = Encoder.ranges[i]["type"]
                min, max = Encoder.ranges[i]["range"]

                if(value >= min and value <= max):
                    self.f.write(i + 1, "uint8")
                    self.f.write(value, type)
                    break

        elif(isinstance(value, bool)):
            self.f.write(0, "uint8")
            self.f.write(1 if value else 0, "uint8")

        elif(isinstance(value, str)):
            try:
                index = lookup[value]
            except KeyError:
                index = 0

            if(index == 0):
                encoded_value = self.encode_run_length(value)
                encoded_length = len(encoded_value)

                if(encoded_length < len(value) and encoded_length <= Encoder.ranges[1]["range"][1]):
                    self.f.write(7, "uint8")
                    self.f.write(encoded_length, "uint16")
                    self.f.write(encoded_value, "plain")
                else:
                    self.f.write(6, "uint8")
                    self.f.write(value, "string")
            else:
                self.f.write(5, "uint8")
                self.f.write(index, "uint16")

    def encode_run_length(self, string):
        count = 0
        res = []
        current = ord(string[0])
        chars = [ord(c[0]) for c in list(string)]

        for char in chars:
            if (char != current or count == 255):
                res.append(count)
                res.append(current)
                count = 1
                current = char
            else:
                count += 1

        res.append(count)
        res.append(current)

        return bytes(res)


class Writer():
    def __init__(self, name):
        self.file = open(name, "wb")

    def write_string(self, data):
        self.write_var_length(len(data))
        self.file.write(data.encode('utf8'))

    def write_var_length(self, length):
        b = []

        while (length > 127):
            b.append(length & 127 | 0b10000000)
            length = math.floor(length / 128)

        b.append(length)
        self.file.write(bytes(b))

    def write_UInt8(self, data):
        d = struct.pack("<B", data)
        self.file.write(d)

    def write_Uint16(self, data):
        d = struct.pack("<H", data)
        self.file.write(d)

    def write_Int16(self, data):
        d = struct.pack("<h", data)
        self.file.write(d)

    def write_Int32(self, data):
        d = struct.pack("<i", data)
        self.file.write(d)

    def write_Float(self, data):
        d = struct.pack("<f", data)
        self.file.write(d)

    def write(self, data, type="string"):
        if(type == "string"):
            self.write_string(data)
        elif(type == "uint8"):
            self.write_UInt8(data)
        elif(type == "uint16"):
            self.write_Uint16(data)
        elif(type == "int16"):
            self.write_Int16(data)
        elif(type == "int32"):
            self.write_Int32(data)
        elif(type == "float"):
            self.write_Float(data)
        else:
            self.file.write(data)

    def close(self):
        self.file.close()


class CelesteMap():
    def __init__(self, file_name="./custom_map.bin"):
        self.header = "CELESTE MAP"

        self.f = Writer(file_name)
        self.e = Encoder(self.f)

        self.f.write(self.header)

    def write_file(self, data=None):
        if(data is None or not isinstance(data, World)):
            raise Exception("Data cannot be None!")

        seen = {}
        data = data.to_formatted_data()

        self.e.populate_encode_key_names(data, seen)

        lookup = list(seen.keys())
        lookup_dict = {k: i for (i, k) in enumerate(lookup)}

        self.f.write(data["_package"], "string")
        self.f.write(len(lookup), "uint16")

        [self.f.write(l, "string") for l in lookup]
        self.e.encode_element(data, lookup_dict)

        self.close()

    def close(self):
        self.f.close()


class World():
    count = 0

    def __init__(self, name="custom"):
        self.name = name

        self.data = {
            "rooms": [],
            "style": Style(),
            "fillers": [],
        }

    def to_formatted_data(self):
        return {
            "_package": self.name,
            "__name": "Map",
            "__children": [
                {
                    "__name": "levels",
                    "__children": [r.to_formatted_data() for r in self.data["rooms"]]
                },
                {
                    "__name": "Style",
                    "__children": self.data["style"].to_formatted_data()
                },
                {
                    "__name": "Filler",
                    "__children": [f.to_formatted_data() for f in self.data["fillers"]]
                }
            ]
        }

    def add_room(self, room):
        self.data["rooms"].append(room)

    def add_filler(self, filler):
        self.data["fillers"].append(filler)

    def set_style(self, style):
        self.data["style"] = style


class Filler():
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def to_formatted_data(self):
        return {
            "__name": "rect",
            "x": self.x, "y": self.y, "w": self.w, "h": self.h
        }


class Style():

    def __init__(self, fg=[], bg=[]):
        self.fg = fg
        self.bg = bg

    def to_formatted_data(self):
        return [
            {
                "__name": "Foregrounds",
                "__children": [f.to_formatted_data() for f in self.fg]
            },
            {
                "__name": "Backgrounds",
                "__children": [b.to_formatted_data() for b in self.bg]
            }
        ]


class Room():
    blacklist = [
        'position',
        'size',
        'color',
        'fgDecals',
        'bgDecals',
        'fgTiles',
        'bgTiles',
        'objTiles',
        'entities',
        'triggers'
    ]

    count = 0

    def __init__(self, name="room_0", size=(40, 23), pos=(0, 0)):
        self.data = {
            "position": [pos[0], pos[1]],
            "_size": [size[0] * 8, size[1] * 8],
            "name": name,
            "entities": [],
            "triggers": [],
            "fgDecals": [],
            "bgDecals": [],
            "fgTiles": "",
            "bgTiles": "",
            "objTiles": "",
            "musicLayer1": False,
            "musicLayer2": False,
            "musicLayer3": False,
            "musicLayer4": False,
            "musicProgress": "",
            "ambienceProgress": "",
            "dark": False,
            "space": False,
            "underwater": False,
            "whisper": False,
            "disableDownTransition": False,
            "delayAltMusicFade": False,
            "music": "music_oldsite_awake",
            "altMusic": "",
            "windPattern": "None",
            "color": 0,
            "cameraOffsetX": 0,
            "cameraOffsetY": 0
        }

        self.room_grid_fg = Shape.Rect(
            (size[0], size[1]), (size[0], size[1])).to_tiles()
        self.room_grid_bg = Shape.Rect(
            (size[0], size[1]), (size[0], size[1])).to_tiles()

        Room.count += 1

    def to_formatted_data(self):
        res = {}

        for field in self.data.keys():
            val = self.data[field]
            if(not field in Room.blacklist):
                res[field] = val

        res["__name"] = "level"
        res["x"] = self.data["position"][0]
        res["y"] = self.data["position"][1]
        res["c"] = self.data["color"]
        res["width"] = self.data["_size"][0]
        res["height"] = self.data["_size"][1]

        res["__children"] = [
            {
                "__name": "solids",
                "innerText": self.room_grid_fg.to_tile_string("0", "")
            },
            {
                "__name": "bg",
                "innerText": self.room_grid_bg.to_tile_string("0", "")
            },
            {
                "__name": "objtiles",
                "innerText": "".join([self.data["objTiles"] if isinstance(self.data["objTiles"], str) else self.data["objTiles"].to_tile_string(-1, ",")])
            },
            {
                "__name": "fgtiles",
                "tileset": "Scenery",
            },
            {
                "__name": "bgtiles",
                "tileset": "Scenery",
            },
            {
                "__name": "entities",
                "__children": [e.to_formatted_data() for e in self.data["entities"]]
            },
            {
                "__name": "triggers",
                "__children": [t.to_formatted_data() for t in self.data["triggers"]]
            },
            {
                "__name": "fgdecals",
                "tileset": "Scenery",
                "__children": []
            },
            {
                "__name": "bgdecals",
                "tileset": "Scenery",
                "__children": []
            },
        ]

        return res

    def add_entity(self, entity):
        self.data["entities"].append(entity)

    def add_tiles(self, tiles, loc="fg"):
        if(loc == "fg"):
            self.room_grid_fg.set_tiles(tiles)
        else:
            self.room_grid_bg.set_tiles(tiles)

    def add_triggers(self, trigger):
        self.data["triggers"].append(trigger)


class Entity():
    blacklist = ["nodes"]

    count = 0

    def __init__(self, name, data, id):
        self.name = name
        self.data = data
        self.id = id

        try:
            self.data["x"] = self.data["x"] * 8
            self.data["y"] = self.data["y"] * 8
        except KeyError:
            raise ValueError("Missing X or Y in entity position!")

        Entity.count += 1

    def to_formatted_data(self):
        res = {}
        res["__name"] = self.name
        res["id"] = self.id

        for key, value in self.data.items():
            if(not key in Entity.blacklist):
                res[key] = value

        try:
            if(len(self.data["nodes"] > 0)):
                res["__children"] = []

                for node in self.data["nodes"]:
                    res["__children"].append({
                        "__name": "node",
                        "x": node[0],
                        "y": node[1],
                    })
        except KeyError:
            pass

        return res


class Trigger(Entity):

    def __init__(self, name, data, id):
        Entity.__init__(self, name, data, id)


class Shape():
    valid_fg_tiles = {
        "Air": 0,
        "Lostlevels": "m",
        "Stone": 6,
    }
    valid_bg_tiles = {
        "Core": "d",
        "Dirt": 1,
    }

    def get_tile_set(type):
        tile_set = None
        try:
            Shape.valid_fg_tiles[type]
            tile_set = Shape.valid_fg_tiles
        except KeyError:
            try:
                Shape.valid_bg_tiles[type]
                tile_set = Shape.valid_bg_tiles
            except KeyError:
                raise ValueError("Unknown tile type %s" % str(type))
        return tile_set

    class Rect():
        def __init__(self, size, room_size, origin=(0, 0), type="Air"):
            room_size = (room_size[1], room_size[0])
            size = (size[0] - 1, size[1] - 1)

            self.tile_array = np.zeros(room_size, dtype=int).tolist()
            tile_set = Shape.get_tile_set(type)

            if(size[0] >= 0 and size[1] >= 0):
                for r in range(0, room_size[0]):
                    for c in range(0, room_size[1]):
                        if(origin[0] <= c < (origin[0] + size[0]) and origin[1] <= r <= (origin[1] + size[1])):
                            self.tile_array[r][c] = tile_set[type]
                        else:
                            self.tile_array[r][c] = tile_set["Air"]
            else:
                raise ValueError("Size cannot be less than 1!")

        def to_tiles(self):
            return Tiles(self.tile_array)

    def plain_tile_array(room_size):
        room_size = (room_size[1], room_size[0])

        tile_array = np.zeros(room_size, dtype=int).tolist()
        return Tiles(tile_array)


class Tiles():

    def __init__(self, array):
        self.tile_array = array

    def set_tiles(self, tile):
        for r in range(0, len(self.tile_array)):
            for c in range(0, len(self.tile_array[0])):
                self.tile_array[r][c] = tile[r][c] if str(
                    tile[r][c]) != "0" else self.tile_array[r][c]

        return self

    def to_tile_string(self, empty="0", sep=","):
        res = []
        rows, cols = [len(self.tile_array), len(self.tile_array[0])]
        rel_rows = 0

        for i in range(0, rows):
            rel_rows = i + 1
            if(not len([o for o in self.tile_array[i] if o != empty])):
                break

        for i in range(0, rel_rows):
            row = self.tile_array[i]
            rel_cols = cols

            for j in range(0, cols):
                if(row[j] != empty):
                    break
                rel_cols -= 1

            res.append(sep.join(str(x) for x in row[0: rel_cols]))

        return "\n".join(res)

    def __getitem__(self, key):
        return self.tile_array[key]

    def __setitem__(self, key, value):
        self.tile_array[key] = value

    def __add__(self, tile):
        return self.set_tiles(tile)

    def __len__(self):
        return len(self.tile_array)


class ObjTiles(Tiles):
    def __init__(self, origin, size, type="Air"):
        Tiles.__init__(self, origin, size, type)


class Cutscene():
    content = """
{variables}
function onBegin()
{on_begin}
end
function onStay(player)
{on_stay}
end
{extras}
    """

    def __init__(self, name="./custom_cutscene.lua"):
        self.f = open(name, "w")

        self.code = {
            "variables": [],
            "on_begin": [],
            "on_stay": [],
            "extras": [],
        }

    def add_on_begin(self, code):
        self.code["on_begin"].append(code)

    def add_on_stay(self, code):
        self.code["on_stay"].append(code)

    def add_variable(self, code):
        self.code["variables"].append(code)

    def add_extra(self, code):
        self.code["extras"].append(code)

    def write_file(self):
        self.f.write(Cutscene.content.format(
            variables="\n".join(self.code["variables"]),
            on_begin="\n".join(self.code["on_begin"]),
            on_stay="\n".join(self.code["on_stay"]),
            extras="\n".join(self.code["extras"])
        ))
        self.f.close()

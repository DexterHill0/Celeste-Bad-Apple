import argparse
import os
from pathlib import Path

import imageio
import cv2
import numpy as np

import map

args = None


def create_map():
    if(not os.path.exists(args.vid)):
        raise IOError("Cannot find video file!")

    path = Path(args.c) / Path("Mods/")

    vid = imageio.get_reader(args.vid)
    fps = vid.get_meta_data(0).get("fps")

    dur = vid.get_meta_data(0).get("duration")

    if(args.f > fps):
        raise ValueError("FPS cannot be greater than %s" % fps)

    file = map.CelesteMap(path / Path(args.n + ".bin"))
    world = map.World("bad_apple")

    offset = args.w // 2 + 4
    w, h = (int((args.w + offset) * (args.f * (round(dur) + 3))),
            int((args.h + offset)))

    print("creating room and floor!")
    room = map.Room("room_0", size=(w, h))
    floor = map.Shape.Rect((20, 1), (w, h), (0, h - 1),
                           type="Stone").to_tiles()
    room.add_tiles(floor)

    print("adding character and triggers!")
    # add spawn point for character
    room.add_entity(map.Entity(
        "player", {"x": 2, "y": h - 1}, map.Entity.count))

    room.add_triggers(map.Trigger("luaCutscenes/luaCutsceneTrigger",
                                  {"x": 3, "y": h - 6, "width": 40, "height": 40, "filename": "cutscene", "unskippable": True}, map.Entity.count))
    room.add_triggers(map.Trigger("eventTrigger", {
                      "x": 50, "y": 50, "width": 40, "height": 40}, map.Entity.count))

    folder = path / Path("cutscenes")
    folder.mkdir(parents=True, exists_ok=True)

    cut = map.Cutscene(path / Path("cutscenes/cutscene.lua"))
    cut.add_variable("""local X = 0
local cam = getRoom().Camera""")

    # from now on every number is just trial and error i dont even know what any are supposed to mean

    y_pos = np.interp(180 / (h*4), [0.1, 1], [420, 0]) - \
        [offset if (180 / (h*4)) > 0.5 else 0][0]

    cut.add_on_stay("""    cam.Y = %s
    cam.X = X""" % y_pos)

    if(not h < 23):
        cut.add_on_begin("""    cam.Zoom = %s""" % (round(180 / (h*5), 2)))
    cut.add_on_begin("""    disableMovement()
    moveCam()
    enableMovement()""")

    print("creating array for tiles!")
    b = map.Shape.plain_tile_array((w, h))

    f_count = 0
    # was playing back at half speed for some bizzare reason
    delay = (1 / (args.f*2))
    total_f_count = 0

    for frame in vid:
        if(f_count >= (fps / args.f)):
            print("processing frame!")

            frame = cv2.resize(frame, dsize=(args.w, args.h),
                               interpolation=cv2.INTER_CUBIC)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            for i, v in np.ndenumerate(frame):
                # trial and error at its finest
                origin = (offset // 2 + i[0],
                          offset // 2 + i[1] + ((args.w + offset) * total_f_count))

                if(v >= 127):
                    b[origin[0]][origin[1]] = "b"
                    #f[origin[0]][origin[1]] = "m"
                else:
                    b[origin[0]][origin[1]] = 1

            f_count = 0
            total_f_count += 1
        f_count += 1

    cut.add_extra("""function moveCam()
    for i=0,{x},{step} do
        X = i
        wait({delay})
    end
end""".format(x=w * 8, step=((args.w + offset) * 8), delay=delay))

    # room.add_tiles(map.Tiles(f))
    room.add_tiles(b, "bg")

    world.add_room(room)

    cut.write_file()
    file.write_file(world)


def setup():
    global args  # ew

    parser = argparse.ArgumentParser(
        description="Creates a Celeste map to play \"Bad Apple!!\"")

    parser.add_argument("--name", "-n", type=str,
                        help="Name of output file", dest="n")
    parser.add_argument("--video", "-vid", type=str,
                        help="Path to video", dest="vid")
    parser.add_argument("--celeste", "-c", type=str,
                        help="Path to Celeste install", dest="c")
    parser.add_argument("--width", "-w", type=int,
                        help="Width of output video", dest="w")
    parser.add_argument("--height", "-he", type=int,
                        help="Height of of output videp", dest="h")
    parser.add_argument("--frames", "-f", type=int,
                        help="Number of frames per second for output video", dest="f")

    args = parser.parse_args()


def main():
    setup()

    create_map()


main()

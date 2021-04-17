# Celeste-Bad-Apple

Must have Python 3 installed and the following libraries installed:

`opencv-python, imageio, numpy`

You must also have Everest installed and [LuaCutscenes](https://gamebanana.com/gamefiles/10788) installed.

##### `badapple.py`

* `--video` / `-vid` The video file to be made into portals - should be completely black and white (i.e. black *or* white but no in between)
* `--width` / `-w` Width of output (in blocks [8 by 8 pixels])
* `--height` / `-he` Height of output (in blocks [8 by 8 pixels])
* `--frames` / `-f` FPS of output
* `--name` / `-n` Name of output map
* `--celeste` / `-c` The path to your Celeste install

To use the `bad_apple.bin` map, simply add it to `<path_to_celeste/Mods/bad_apple.bin`. Run Everest and enable debug mode. Navigate to debug maps and open the map.

Every frame is made up of background tiles and your camera's X position is incremented to show each frame one after the other with a delay in between.  

Originally I tried a 200x200 video but I ran out of memory while creating the numpy array. Same went for 150x150, 120x120 but not 100x100. Unfortunately, Celeste then ran out of memory while opening the map so I found that about **95x95** is the largest that can be created.

It also modifies the camera's zoom to fit more on screen but the downside to that is that the resolution stays the same so it becomes very pixelated.


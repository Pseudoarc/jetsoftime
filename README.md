# Jets of Time: An Open World Chrono Trigger Randomizer
Jets of Time is a remake of Wings of Time, an open world Chrono Trigger randomizer.  Liberties have been taken with the gameplay to decrease seed time and to accommodate the open world, but it is still mostly classic Chrono Trigger.

Online Seed Generator: https://www.ctjot.com  
Discord: https://discord.gg/cKYjHwj  
Wiki: https://wiki.ctjot.com/  (May be out of date for some beta changes)

## USAGE

Run `python3 randomizer.py -h` for a full list of options.  The most simple invokation is `python3 randomizer.py -i ct.sfc` where `ct.sfc` is a vanilla US Chrono Trigger rom.  A gui can be invoked with `python3 randomizergui.py`.   Windows users should use `python.exe` rather than `python3`.  Python >=3.8 is required and can be obtained for free at https://www.python.org/downloads/. An alternate gui which is designed to work with handhelds can be found here: https://github.com/Aerovet/JetsOfTimeTravel.

## Building
Excecutables are packaged with each release.  Windows users who desire to build their own executable can follow the following steps:
* Since we will install extra modules, it is recommended to work in a virtual environment.  Discussion of virtual environments is outside the scope of this document.  See https://docs.python.org/3/library/venv.html for the full details.
* If you  are using a virtual environment, be sure to activate it prior to running the commands below.
* From the command line run `pip.exe install nuitka`
* After nuitka is installed, run `python.exe -m nutika randomizergui.exe` in the `sourcefiles` directory.  This will create `randomizergui.exe` in the `sourcefiles` directory.
* Nuitka can create a standalone installation with `python.exe -m nuitka --standalone --enable-plugin=tk-inter`.  This will create a folder called `randomizergui.dist` in which the executable will be located.  The `patches`, `flux`, and `pickles` folders must also be copied
into the `randomizergui.dist` folder.

## Credits
Most contributions can be seen in the commit history, but special thanks go:
* Mauron, Myself086, and Lagolunatic for general technical assistance; 
* Abyssonym for initial work on Chrono Trigger randomization (Eternal Nightmare, Wings of Time); and 
* Anskiy for originally inventing Jets of Time and developing the initial set of open world event scripts.

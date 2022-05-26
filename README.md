# nkc-cas-writer

## Introduction
<p>This repository contains a simple program to convert compiled binary files into the casette forat of the NDR-Klein-Computer of the 1980s. </p>
Currently the generated files are binary and can be used with the NKC-Emulator of Torsten Evers. See his [GitHub](https://github.com/Nightwulf/NKCEmu) page.

Also we only support the cassete data format of the GRUNDPROGRAMM. Cassete format of Basic programs may be added later if it can be reversed engineered.

## Usage

usage: caswriter.py [-h] [-n NAME] [-s START] [binFile]

positional arguments:
  binFile               Datei mit dem kompilierten Programm im binärformat

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Name der Kasseten-Aufzeichnung, Default ist der Dateiname in Grossbuchtaben
  -s START, --start START
                        Start Addresse des Daten (default 0x8800)
						
## Future enhanment
I plan to add an output in WAV format which then can be used to playback the file and load thus the original computer.
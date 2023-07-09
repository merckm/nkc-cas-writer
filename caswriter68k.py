
import string
import sys
import argparse
import logging
import tokenize
from pathlib import Path
import baswriter


def main() -> int:

    #    logging.basicConfig(filename='caswriter.log',
    #                        format='%(asctime)s %(message)s', level=logging.DEBUG)

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='?',
                        help="Datei mit dem Programm im Textformat")
    parser.add_argument("-n", "--name", type=str,
                        help="Name der Kasseten-Aufzeichnung, Default ist der Dateiname in Grossbuchtaben")

    args = parser.parse_args()

    baseName = Path(args.filename).stem
    recordingName = baseName.upper()
    if args.name != None:
        recordingName = args.name.upper()

    print(f"Converting file:      {args.filename}")
    print(f"Writing file:         {baseName+'.cas'}")

    print(f"Using recording name: {recordingName}")

    # Create cassette recording name section
    # ======================================
    filler1 = bytearray([0xFF] * 40)
    filler2 = bytearray([0xFF] * 32)
    filler3 = bytearray([0xFF] * 21)
    nameTag = bytearray([
        0x00, 0x2F
    ])
    name = bytearray(recordingName + "\r", encoding='ascii')
    nameSection = filler1 + nameTag + name

    # Create data section
    # ===================
    data = bytearray([ 0x00 ])
    file = open(args.filename, "rb")
    try:
        data += file.read()
    except (OSError, IOError) as e:
        logging.error('File could not be read!')
        sys.exit(-1)

    data += b'\x00'
    file.close()

    dataCheck = 0
    for byte in data:
        dataCheck += byte
    dataCheck &= 0xFFFF

    dataSection = filler2
    dataSection += data + dataCheck.to_bytes(2, 'big', signed=False)

    print(f"Total data bytes:     {len(data)}")

    symbolSect = filler3

    # Create cas file binary
    casfile = nameSection + dataSection + symbolSect
    casFileName = baseName + ".cas"
    with open(casFileName, "wb") as out_file:
        out_file.write(casfile)

    return 0


if __name__ == '__main__':
    sys.exit(main())

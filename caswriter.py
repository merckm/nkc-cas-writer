
import string
import sys
import argparse
import logging
from pathlib import Path


def main() -> int:

    startSymboltabelle = 0x81C1         # Wert aus NKC-Emulator

    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('binFile', nargs='?',
                        help="Datei mit dem kompilierten Programm im binärformat",
                        type=argparse.FileType('rb'))
    parser.add_argument("-n", "--name", type=str,
                        help="Name der Kasseten-Aufzeichnung, Default ist der Dateiname in Grossbuchtaben")
    parser.add_argument("-s", "--start",
                        help="Start Addresse des Daten (default 0x8800)", type=int, default=0x8800)
    args = parser.parse_args()

    baseName = Path(args.binFile.name).stem
    recordingName = baseName.upper()
    if args.name != None:
        recordingName = args.name.upper()

    print(f"Converting file:      {args.binFile.name}")
    print(f"Writing file:         {baseName+'.cas'}")
    print(f"Using recording name: {recordingName}")

    # Create cassette recording name section
    # ======================================
    filler = bytearray([0xFF] * 20)
    nameTag = bytearray([
        0x00, 0x2F
    ])
    name = bytearray(recordingName + "\r", encoding='ascii')
    nameSection = filler + filler + nameTag + name

    # Create data section
    # ===================
    dataTag = bytearray([
        0x00, 0x3A
    ])
    data = args.binFile.read()

    startAdr = args.start
    endAdr = startAdr + len(data) - 1
    startAddress = startAdr.to_bytes(2, 'big')
    endAddress = endAdr.to_bytes(2, 'big')

    dataCheck = 0
    dataCheck += startAdr
    dataCheck += endAdr
    for byte in data:
        dataCheck += byte
    dataCheck &= 0xFFFF

    dataSection = filler + dataTag + startAddress + endAddress
    dataSection += data + dataCheck.to_bytes(2, 'big', signed=False)

    print(f"Total data bytes:     {len(data)}")

    # Create symbols section
    # ======================
    symbolTag = bytearray([
        0x00, 0x24
    ])

    symbols = []
    offsets = []

    symbolSection = False
    try:
        with open(baseName+".lst", 'r', encoding='ASCII') as file:
            for line in file:
                if "Symbols:" in line:
                    symbolSection = True
                    continue
                if len(line.strip()) == 0:
                    symbolSection = False
                if symbolSection:
                    tokens = line.split()
                    if(tokens[-1] == 'ABS'):
                        try:
                            address = int(
                                line[line.find("(")+1:line.find("=")])
                        except ValueError as verr:
                            logging.error(
                                f"Could not get address from line {line}.\nIgnoring Symbol.")
                            continue
                        symbols.append(tokens[0])
                        offsets.append(address)
    except (OSError, IOError) as e:
        logging.warning('Could not open Listing file!')

    if len(symbols) == 0:
        logging.info(
            "No symbols found. Adding default sympol START to point to start address")
        symbols.append("START")
        offsets.append(startAdr)

    for i in range(len(symbols)):
        print(
            f"Added Symbol@Offste:  {symbols[i]}@{hex(offsets[i])}")

    startSymbols = startSymboltabelle.to_bytes(2, 'big')
    nextSymbol = startSymboltabelle
    # 8bytes are used for 'num symbols', 'next free' ptr and 'signature bytes'
    nextSymbol += 8
    for symbol in symbols:
        # Length of symbol name + address pointer
        nextSymbol += len(symbol) + 2

    endSymbols = nextSymbol.to_bytes(2, 'big')
    symCheck = startSymboltabelle
    symCheck += nextSymbol

    symbolsString = bytearray()
    symbolsString += len(symbols).to_bytes(2, 'little')
    symbolsString += nextSymbol.to_bytes(2, 'little')
    symbolsString += bytearray([
        0x55, 0xAA, 0x01, 0x80
    ])

    for index in range(len(symbols)):
        symbolBytes = bytearray(symbols[index], encoding='ascii')
        symbolBytes[-1] |= 0x80
        symbolsString += symbolBytes
        symbolsString += offsets[index].to_bytes(2, 'little')

    symbolsString.append(0)

    for symbolByte in symbolsString:
        symCheck += symbolByte
    symCheck &= 0xFFFF

    symbolSect = filler + symbolTag + startSymbols + endSymbols
    symbolSect += symbolsString + symCheck.to_bytes(2, 'big', signed=False)
    symbolSect += filler

    # Create cas file binary
    casfile = nameSection + dataSection + symbolSect
    casFileName = baseName + ".cas"
    with open(casFileName, "wb") as out_file:
        out_file.write(casfile)

    return 0


if __name__ == '__main__':
    sys.exit(main())


from multiprocessing.managers import SyncManager
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
                        help="Datei mit dem Programm bei Assembler im Binärformat, bei GOSI oder BASIC im Textformat")
    parser.add_argument("-n", "--name", type=str,
                        help="Name der Kasseten-Aufzeichnung, Default ist der Dateiname in Grossbuchtaben")
    parser.add_argument("-s", "--start",
                        help="Start Addresse des Daten (default 0x8800)", type=lambda x: int(x, 0), default=0x8800)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-g', "--gosi", action='store_true',
                       help="GOSI Mode. Konvertiere GOSI Datei, defaul is Assembler")
    group.add_argument('-b', "--basic", action='store_true',
                       help="BASIC Mode. Konvertiere BASIC Datei, defaul is Assembler")

    args = parser.parse_args()

    if args.gosi:
        logging.info("Running in GOSI Mode")

    if args.basic:
        logging.info("Running in BASIC Mode")

    baseName = Path(args.filename).stem
    recordingName = baseName.upper()
    if args.name != None:
        recordingName = args.name.upper()

    print(f"Converting file:      {args.filename}")
    print(f"Writing file:         {baseName+'.cas'}")

    if args.basic:
        baswriter.writeBas(baseName)
        sys.exit(0)

    print(f"Using recording name: {recordingName}")

    symbols = []
    offsets = []
    symtype = []

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
    if(not args.gosi and not args.basic):
        file = open(args.filename, "rb")
        data = file.read()
        file.close()

    if args.gosi:
        data = bytearray([])
        file = open(args.filename, "r", encoding="utf-8")
        try:
            for line in file:
                currAdr = 0x8600 + len(data)
                tokens = line.rstrip().split()
                # Find symbols and encode
                lernmode = False
                foundTokens = []
                for i in range(len(tokens)):
                    # Find symbols in GOSI file by seahing for keyword "LERNE"
                    if i == 0 and tokens[0].upper() == "LERNE":
                        symbols.append(tokens[1].upper())
                        offsets.append(currAdr)
                        symtype.append(b'\x02')
                        line = line[5:].lstrip()
                        lernmode = True
                    if (tokens[i].upper() in symbols) and not lernmode:
                        index = symbols.index(tokens[i].upper())
                        if symtype[index] == b'\x02':
                            foundTokens.append(tokens[i])
                    firstChar = tokens[i][0]
                    if (firstChar == '"' or firstChar == ':'):
                        varName = ""
                        for char in tokens[i][1:].upper():
                            if char.isalpha():
                                varName += char
                        if not varName in symbols:
                            symbols.append(varName)
                            offsets.append(0)
                            symtype.append(b'\x01')
                # print(line, end='')
                stringBytes = bytearray(line.rstrip(), encoding="ascii")
                for sym in foundTokens:
                    pos = line.find(sym)
                    while pos != -1:
                        stringBytes[pos] |= 0x80
                        pos = line.find(sym, pos+1)
                data += stringBytes
                data += b'\x00'
            data += b'\x00'
        except (OSError, IOError) as e:
            logging.error('GOSI file could not be read!')
            sys.exit(-1)
        file.close()

    startAdr = args.start
    if args.gosi:
        startAdr = 0x8600
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
    startSymboltabelle = 0x81C1         # Wert aus NKC-Emulator
    if(args.gosi):
        startSymboltabelle = 0x8341     # Wert aus NKC-Emulator

    symbolTag = bytearray([
        0x00, 0x24
    ])

    if(not args.gosi and not args.basic):
        symbolSection = False
        try:
            with open(baseName+".lst", 'r') as file:
                for line in file:
                    if "Symbols:" in line:
                        symbolSection = True
                        continue
                    if len(line.strip()) == 0:
                        symbolSection = False
                    if symbolSection:
                        # ignore inner symbols starting with a dot
                        if line[0] == ' ':
                            continue
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

    # In GOSI 3 addresses are added to the symbol table to mark the interpreter buffer
    if (args.gosi):
        nextSymbol += 6
    # 8bytes are used for 'num symbols', 'next free' ptr and 'signature bytes'
    nextSymbol += 8

    for symbol in symbols:
        # Length of symbol name + address pointer
        nextSymbol += len(symbol) + 2
        # In GOSI we also have one byte for symbol type
        if (args.gosi):
            nextSymbol += 1

    sizeSymbols = nextSymbol-startSymboltabelle
    if(sizeSymbols > 575):
        logging.error(f'Symbol table is to big: {sizeSymbols} bytes!')
        sys.exit(-1)

    endSymbols = nextSymbol.to_bytes(2, 'big')
    symCheck = startSymboltabelle
    symCheck += nextSymbol

    symbolsString = bytearray()
    if args.gosi:
        symbolsString += startAdr.to_bytes(2, 'little')
        symbolsString += endAdr.to_bytes(2, 'little')
        symbolsString += 0x8FFF.to_bytes(2, 'little')

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
        if args.gosi:
            symbolsString += symtype[index]

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

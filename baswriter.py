import logging
import sys
from re import sub

keywords = ["END", "FOR", "NEXT", "DATA", "INPUT", "DIM", "READ", "LET", "GOTO", "RUN",
            "IF", "RESTORE", "GOSUB", "RETURN", "REM", "STOP", "OUT", "ON", "NULL", "WAIT",
            "POKE", "PRINT", "DEF", "CONT", "LIST", "CLEAR", "CLOAD", "CSAVE", "NEW", "BYE",
            "LLIST", "LPRINT", "CALL", "CLRS", "MOVETO", "DRAWTO", "PAGE", "TAB", "TO",
            "SPC", "FN", "TI$", "THEN", "NOT", "STEP", "+", "-", "*", "/", "^", "AND",
            "OR", ">", "=", "<", "SGN", "INT", "ABS", "USR", "FRE", "INP", "POS", "SQR",
            "RND", "LOG", "EXP", "COS", "SIN", "TAN", "ATN", "PEEK", "LEN", "STR$", "VAL",
            "ASC", "CHR$", "HEX", "LEFT$", "RIGHT$", "MID$", "?"]


def writeBas(basename):
    memOffset = 0x88C5
    dataSection = bytearray([])
    try:
        file = open(basename+".bas", "r", encoding="utf-8")
        for line in file:

            casLine = bytearray([])

            # skip empty lines
            if (len(line) == 0):
                continue

            lineNumber = ""
            linePos = 0
            for character in line:
                if character.isdigit():
                    lineNumber += character
                else:
                    if not character.isspace():
                        break
                linePos += 1

            if len(lineNumber) == 0:
                print(f"Syntax error in Lline {line}, expected line number")

            lineNum = int(lineNumber)
            casLine += lineNum.to_bytes(2, 'little')

            # Create a dictonary of all occurances of BASIC Keywords
            # Some Keywords are substrings of other keywords (e.f. INP from INPUT)
            # We assume that they are ordered in the list with the longest
            # keyword first to make sure we don't have to hanle this here
            keysDict = {}
            for keyword in keywords:
                codeLine = line.rstrip().upper()
                posOffset = 0
                while keyword in codeLine:
                    pos = codeLine.find(keyword)
                    char = 0x80 + keywords.index(keyword)
                    if(not(pos in keysDict)):
                        keysDict[pos+posOffset] = keyword
                    codeLine = codeLine[pos+len(keyword):]
                    posOffset = posOffset+pos+len(keyword)

            logging.debug(keysDict)
            # Sort the dictonary by position in line (creates a list)
            keyList = sorted(keysDict.items(), key=lambda x: x[0])
            logging.debug(keyList)

            # remove overlapping elements
            newList = []
            oldpos = linePos        # skip line number
            for pos, keyword in keyList:
                logging.debug(f"[´{keyword} at {pos} with old:{oldpos}")
                if pos >= oldpos:
                    newList.append([pos, keyword])
                oldpos = pos + len(keyword)
            logging.debug(newList)

            codeLine = line.rstrip()
            oldpos = linePos        # skip line number
            for pos, keyword in newList:
                if(pos > oldpos):
                    # Add characters between Keywords unchanged
                    substring = codeLine[oldpos:pos]
                    casLine += bytearray(substring, encoding="ascii")

                char = 0x80 + keywords.index(keyword)
                # If we winf the '?' symbol we treat it as a PRINT instrubtion
                if char == 0xD0:
                    char = 0x95
                casLine += char.to_bytes(1, 'big')
                oldpos = pos + len(keyword)
                # Break loop if keyword is REM, Rest of line will be taking as literal
                if keyword == "REM":
                    break

            # Add the rest of the line
            substring = codeLine[oldpos:]
            casLine += bytearray(substring, encoding="ascii")

            casLine += b'\x00'
            logging.info(casLine)
            memOffset += len(casLine)
            dataSection += memOffset.to_bytes(2, 'little') + casLine

    except (OSError, IOError) as e:
        logging.error('BASIC file could not be read!')
        sys.exit(-1)

    file.close()

    # Create cas file binary
    filler = bytearray([0x00] * 5)
    tag = bytearray([0xD3] * 3)
    startSection = filler + filler + tag + bytearray([0x00])
    endSection = filler

    casfile = startSection + dataSection + endSection
    casFileName = basename+".cas"
    with open(casFileName, "wb") as out_file:
        out_file.write(casfile)

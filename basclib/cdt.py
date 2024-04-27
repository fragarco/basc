"""
Simple tool to add content to Amstrad CDT files.
INFO about the CDT file format can be read here:
https://www.cpcwiki.eu/index.php/Format:CDT_tape_image_file_format

Information about how information in stored in real tapes can be
found in the Firmware guide (chapter 8):
https://archive.org/details/SOFT968TheAmstrad6128FirmwareManual

As per de documentation, timings are expected as Z80 clock ticks (T states)
unless otherwise stated. 1 T state = (1/4000000)s (CPC Z80 ran at 4 Mhz)
"""

import sys
import argparse
import math

AMSDOS_BAS_TYPE = 0
AMSDOS_PROTECTED_TYPE = 1
AMSDOS_BIN_TYPE = 2

DEF_DATA_BLOCK_SZ = 2048   # max size for a data block (2K)
DEF_DATA_SEGMENT_SZ = 256
DEF_DATA_TRAIL = [0xFF, 0xFF, 0xFF, 0xFF]
DEF_WRITE_SPEED = 2000  # 1000 is another common value
DEF_PAUSE_HEADER = 15   # ms
DEF_PAUSE_DATA  = 2560  # ms
DEF_PAUSE_FILE  = 12000 # ms

def AUX_GET_CRC(data):
    """
    Auxiliary function that calculates the CRC on 256 bytes of data
    using CRC-16-CCITT Polynomial: X^16+X^12+X^5+1 and an initial 
    seed 0xFFFF
    """
    crc = 0xFFFF
    for i in range(0, 256):
        k = crc >> 8 ^ data[i]
        k = k ^ k >> 4
        crc = crc << 8 ^ k << 12 ^ k << 5 ^ k
        crc	= crc & 0xFFFF
    crc = crc ^ 0xFFFF		
    return crc

def AUX_BAUDS2PULSE(speed):
    # Let's calculate de pulse time in nanoseconds following the
    # firmware guide
    pulse = 333333 / speed
    # following the CDT format guide lets calculate the pulse
    # as CPU cycles (aka T steps): (pulse / 1000000) * 3500000
    return math.ceil(pulse * 3.5)

class FormatError(Exception):
    """
    Raised when procesing a file and its format is not the expected one.
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class CDTHeader:
    """
    Encapsulates the header of a CDT file. It compromises the first 10 bytes.
    0       "ZXTape!"
    7       0x1A
    8       Major version number
    9       Minor version number
    """
    def __init__(self):
        self.title = "ZXTape!"
        self.major = 1
        self.minor = 13

    def compose(self):
        # Total size of 10 bytes
        header = bytearray(self.title.encode('utf-8'))
        header.extend(b'\x1A')
        header.extend(self.major.to_bytes(1, 'little'))
        header.extend(self.minor.to_bytes(1, 'little'))
        return header

    def set(self, content):
        if len(content) < 10:
            raise FormatError("header size is less than 10 bytes")
        self.title = content[0:7].decode('utf-8')
        self.major = int(content[8])
        self.minor = int(content[9])
        return content[10:]
    
    def check(self):
        if "ZXTape!" not in self.title:
            raise FormatError("CDT header title doesn't contain 'ZXTape!' text")

    def dump(self):
        print("CDT HEADER title:", self.title, "version:", self.major, '.', self.minor)

class DataHeader:
    """
    Encapsulates de header for CDT data blocks. It starts with
    the sync byte 0x2C

    Header (28 bytes):
 	00  16   Filename (padded with 0x00)
    10   1   block ID (1,2,3...)
 	11   1   Last block? (0xFF or 0x00)
    12   1   Type (0x00: BAS, 0x01: Protected, 0x02: BIN, 0x16: ASCII)
    13   2   Block size
    15   2   Start + past blocks (loading address for this block)
    17   1   First block? (0xFF or 0x00)
    19   2   Length
    1B   2   call address
    """

    FT_BAS = 0x00
    FT_BIN = 0x02
    FT_ASCII = 0x16
    SYNC  = 0x2C

    def __init__(self):
        self.filename = "UNNAMED"
        self.block_id = 1
        self.last_block = 0x00
        self.type = self.FT_BIN
        self.block_sz = 1+256+2+4  # segment sync + size + CRC + trail
        self.addr_load = 0
        self.first_block = 0xFF
        self.length = 0
        self.addr_start = 0x4000

    def set(self, content):
        self.filename = content[0:16].decode('utf-8')
        self.block_id = int(content[16])
        self.last_block = int(content[17])
        self.type = int(content[18])
        self.block_sz = int.from_bytes(content[19:21], 'little')
        self.addr_load = int.from_bytes(content[21:23], 'little')
        self.first_block = int(content[23])
        self.length = int.from_bytes(content[24:26], 'little')
        self.addr_start = int.from_bytes(content[26:28], 'little')
        # Segments are always of 256 bytes plus CRC (2) and trail (4)
        return content[256+2+4:]

    def compose(self):
        content = bytearray()
        content.extend(b'\x2C')    # sync byte
        name = bytearray(self.filename[0:16].encode('utf-8'))
        name.extend(0x00 for i in range(len(name), 16))
        content.extend(name)
        content.extend(self.block_id.to_bytes(1, 'little'))
        content.extend(self.last_block.to_bytes(1, 'little'))
        content.extend(self.type.to_bytes(1, 'little'))
        content.extend(self.block_sz.to_bytes(2, 'little'))
        content.extend(self.addr_load.to_bytes(2, 'little'))
        content.extend(self.first_block.to_bytes(1, 'little'))
        content.extend(self.length.to_bytes(2, 'little'))
        content.extend(self.addr_start.to_bytes(2, 'little'))
        # segment must be of 256 bytes plus the sync byte
        content.extend(0x00 for i in range(len(content), 256 + 1))
        # but CRC only on data
        crc = AUX_GET_CRC(content[1:])
        content.extend(crc.to_bytes(2, 'big'))  # !!! here MSB first
        content.extend(b'\xFF\xFF\xFF\xFF')     # trail
        return content

    def dump(self):
        print("Name:", self.filename.encode('utf-8'), "type:", hex(self.type), "Number:", self.block_id)
        print("Size:", self.block_sz, "First:", hex(self.first_block), "Last:", hex(self.last_block))
        print("Load Addr:", hex(self.addr_load), "Call addr:", hex(self.addr_start), "Length:", self.length)

    def check(self):
        pass

class BlockNormalSpeed:
    """
    00 2  Pause After this block in milliseconds (ms)
    02 2  Length of following data
    04 x  Data
    """
    ID = 0x10

    def __init__(self, pause = DEF_PAUSE_DATA):
        self.pause = pause
        self.data = bytearray()

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(self.pause.to_bytes(2, 'little'))
        content.extend(len(self.data).to_bytes(2, 'little'))
        content.extend(self.data)
        return content
    
    def set(self, content):
        self.pause = int.from_bytes(content[0:2], 'little')
        sz = int.from_bytes(content[2:4], 'little')
        self.data = content[4:4+sz]
        return content[4+sz:]

    def dump(self):
        print("Data block of standard speed (id 0x10), data (bytes)", len(self.data))

    def check(self):
        pass

class BlockTurboSpeed:
    """
    00 2  Length of PILOT pulse
    02 2  Length of SYNC First pulse
    04 2  Length of SYNC Second pulse
    06 2  Length of ZERO bit pulse
    08 2  Length of ONE bit pulse
    0A 2  Length of PILOT tone (in PILOT pulses)
    0C 1  Used bits in last byte (other bits should be 0)
    0D 2  Pause After this block in milliseconds (ms)
    0F 3  Length of following data
    12 x  Data; format is as for TAP (MSb first)

    All lengths are given in T states:
    Pilot pulse, length  Sync1    Sync2    Bit-0    Bit-1
    ------------------------------------------------------
      Bit-1       4096   Bit-0    Bit-0      *        *
    
    * Amstrad CPC ROM Load/Save routine can use variable speed for loading,
    so the Bit-1 pulse must be read from the Pilot Tone and Bit-0 can be read
    from the Sync pulses, and is always half the size of Bit-1.
    The speed can vary from 1000 to 2000 baud. 
    """
    ID = 0x11

    def __init__(self, speed = DEF_WRITE_SPEED, pause = DEF_PAUSE_DATA):
        bit0 = AUX_BAUDS2PULSE(speed)
        bit1 = bit0 * 2
        self.pilot_len = bit1
        self.sync1_len = bit0
        self.sync2_len = bit0
        self.zero_len = bit0
        self.one_len = bit1
        self.ppulses_count = 4096
        self.used_bits = 8 
        self.pause = pause
        self.data = bytearray()

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(self.pilot_len.to_bytes(2, 'little'))
        content.extend(self.sync1_len.to_bytes(2, 'little'))
        content.extend(self.sync2_len.to_bytes(2, 'little'))
        content.extend(self.zero_len.to_bytes(2, 'little'))
        content.extend(self.one_len.to_bytes(2, 'little'))
        content.extend(self.ppulses_count.to_bytes(2, 'little'))
        content.extend(self.used_bits.to_bytes(1, 'little'))
        content.extend(self.pause.to_bytes(2, 'little'))
        content.extend(len(self.data).to_bytes(3, 'little'))
        content.extend(self.data)
        return content
    
    def set(self, content):
        self.pilot_len = int.from_bytes(content[0:2], 'little')
        self.sync1_len = int.from_bytes(content[2:4], 'little')
        self.sync2_len = int.from_bytes(content[4:6], 'little')
        self.zero_len = int.from_bytes(content[6:8], 'little')
        self.one_len = int.from_bytes(content[8:10], 'little')
        self.ppulses_count = int.from_bytes(content[10:12], 'little')
        self.used_bits = content[12]
        self.pause = int.from_bytes(content[13:15], 'little')
        sz = int.from_bytes(content[15:18], 'little')
        self.data = content[18:18+sz]
        return content[18+sz:]

    def dump(self):
        print("Data block of turbo speed (id 0x11), data block (bytes)", len(self.data))
        print( "Lenghts: pilot %d sync1 %d sync2 %d zero %d one %d pulses %d pause %d"
              %(self.pilot_len, self.sync1_len, self.sync2_len, self.zero_len, self.one_len, self.ppulses_count, self.pause))
        if self.data[0] == 0x2C:
            header = DataHeader()
            header.set(self.data[1:])
            header.dump()
        elif self.data[0] == 0x16:
            print("Data block with 0x16 sync code")
        else:
            print("Uknown sync code:", hex(self.data[0]))
        print("")

    def check(self):
        pass

class BlockPureTone:
    """
    00 2  Length of pulse in T-States
    02 2  Number of pulses
    """
    ID = 0x12

    def __init__(self):
        self.length = 0
        self.pulses = 0

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(self.length.to_bytes(2, 'little'))
        content.extend(self.pulses.to_bytes(2, 'little'))
        return content

    def set(self, content):
        self.length = int.from_bytes(content[0:2], 'little')
        self.pulses = int.from_bytes(content[2:4], 'little')
        return content[4:]
    
    def dump(self):
        print("Pure tone (id 0x12), pulse length:", self.length, "number of pulses:", self.pulses)

    def check(self):
        pass

class BlockDifferentPulses:
    """
    00 1  Number of pulses
    01 2  Length of first pulse in T-States
    03 2  Length of second pulse...
    .. .  etc.
    - Length: [00]*02+01
    """
    ID = 0x13

    def __init__(self):
        self.lengths = []

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(len(self.lengths).to_bytes(1, 'little'))
        for length in self.lengths:
            content.extend(length.to_bytes(2, 'little'))
        return content

    def set(self, content):
        pulses = int(content[0])
        self.lengths = []
        for i in range(0, pulses):
            value = int.from_bytes(content[i*2 + 1: (i+1)*2 + 1], 'little')
            self.lengths.append(value)
        return content[pulses*2+1:]
    
    def dump(self):
        print("Different pulses (id 0x13), number of pulses:", len(self.lengths))

    def check(self):
        pass

class BlockPureData:
    """
    00 2  Length of ZERO bit pulse
    02 2  Length of ONE bit pulse
    04 1  Used bits in LAST Byte
    05 2  Pause after this block in milliseconds (ms)
    07 3  Length of following data
    0A x  Data (MSb first)
    """
    ID = 0x14

    def __init__(self, speed = DEF_WRITE_SPEED, pause = DEF_PAUSE_DATA):
        self.zerop = AUX_BAUDS2PULSE(speed)
        self.onep = self.zerop * 2
        self.used = 8
        self.pause = pause
        self.data = bytearray()

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(self.zerop.to_bytes(2, 'little'))
        content.extend(self.onep.to_bytes(2, 'little'))
        content.extend(self.used.to_bytes(1, 'little'))
        content.extend(self.pause.to_bytes(2, 'little'))
        content.extend(len(self.data).to_bytes(3, 'little'))
        content.extend(self.data)
        return content

    def set(self, content):
        self.zerop = int.from_bytes(content[0:2], 'little')
        self.onep = int.from_bytes(content[2:4], 'little')
        self.used = int(content[4])
        self.pause = int.from_bytes(content[5:7], 'little')
        sz = int.from_bytes(content[7:10], 'little')
        self.data = content[10:10+sz]
        return content[10+sz:]
    
    def dump(self):
        print("Pure data (id 0x14), total data (bytes):", len(self.data))

    def check(self):
        pass

class BlockPause:
    """
    000 2  Pause time in ms
    """
    ID = 0x20

    def __init__(self, pause = 3000):
        self.pause = pause

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(self.pause.to_bytes(2, 'little'))
        return content

    def set(self, content):
        self.pause = int.from_bytes(content[0:2], 'little')
        return content[2:]
    
    def dump(self):
        print("Pause (id 0x20), time (ms):", self.pause)

    def check(self):
        if self.pause < 0:
            raise FormatError("negative pause time in Pause block")

class BlockGroupStart:
    """
    00 1  Length of the Group Name
    01 x  Group name in ASCII (please keep it under 30 characters long)
    """
    ID = 0x21

    def __init__(self):
        self.name = ""

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(len(self.name[0:30]).to_bytes(1, 'little'))
        if len(self.name):
            content.extend(self.name[0:30].encode('utf-8'))
        return content

    def set(self, content):
        sz = int(content[0])
        self.name = "" if sz == 0 else content[1:sz+1].decode('utf-8')
        return content[sz+1:]
    
    def dump(self):
        print("GroupStart (id 0x21), name:", self.name if len(self.name) else "(void)")

    def check(self):
        pass

class BlockGroupEnd:
    """
    This block has no body
    """
    ID = 0x22

    def compose(self):
        return self.ID.to_bytes(1, 'little')
    
    def set(self, content):
        return content

    def dump(self):
        print("GroupEnd (id 0x22)")

    def check(self):
        pass

class BlockDescription:
    """
    00 1  Length of the Text
    01 x  Text in ASCII
    """
    ID = 0x30

    def __init__(self):
        self.text = ""

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        content.extend(len(self.text[0:256]).to_bytes(1, 'little'))
        content.extend(self.text[0:256].encode('utf-8'))
        return content

    def set(self, content):
        sz = int(content[0])
        self.text = content[1:sz+1].decode('utf-8')
        return content[sz+1:]

    def dump(self):
        print("Description (id 0x30), text:", self.text)

    def check(self):
        pass

class BlockArchiveInfo:
    """
    00 2  Length of the block (without these two bytes)
    02 1  Number of text strings
    03 x  Text strings:
        00 1  Text Identification byte:  00 - Full Title
                                         01 - Software House / Publisher
                                         02 - Author(s)
                                         03 - Year of Publication
                                         04 - Language
                                         05 - Game/Utility Type
                                         06 - Price
                                         07 - Protection Scheme / Loader
                                         08 - Origin
                                         FF - Comment(s)
        01 1  Length of text
        02 x  Text in ASCII format
        .. .  Next Text
    
    Length: [00,01]+02
    """
    FULLTITLE   = 0x00
    PUBLISHER   = 0x01
    AUTHOR      = 0x02
    YEAR        = 0x03
    LANGUAJE    = 0x04
    TYPE        = 0x05
    PRICE       = 0x06
    LOADER      = 0x07
    ORIGIN      = 0x08
    COMMENT     = 0xFF
    ID          = 0x32

    def __init__(self):
        self.strings = []

    def add_string(self, type, string):
        self.strings.append((type, string[0:256]))

    def compose(self):
        content = bytearray()
        content.extend(self.ID.to_bytes(1, 'little'))
        strings = bytearray()
        strings.extend(len(self.strings).to_bytes(1, 'little'))
        for s in self.strings:
            strings.extend(s[0].to_bytes(1, 'little'))
            strings.extend(len(s[1]).to_bytes(1, 'little'))
            strings.extend(s[1].encode('utf-8'))
        content.extend(len(strings).to_bytes(2, 'little'))
        content.extend(strings)
        return content

    def set(self, content):
        # remove block size
        content = content[2:]
        strings = content[0]
        content = content[1:]
        self.strings = []
        while strings > 0:
            type = content[0]
            sz = content[1]
            text = content[2:2+sz].decode('utf-8')
            self.strings.append((type, text))
            strings = strings - 1
            content = content[0:2+sz]
        return content
    
    def dump(self):
        print("ArchiveInfo (id 0x32), strings:", len(self.strings))
        for s in self.strings:
            print("Type", hex(s[0]), "value:", s[1])
        
class CDT:

    BLOCKS = {
        BlockNormalSpeed.ID: BlockNormalSpeed,
        BlockTurboSpeed.ID: BlockTurboSpeed,
        BlockPureTone.ID: BlockPureTone,
        BlockDifferentPulses.ID: BlockDifferentPulses,
        BlockPureData.ID: BlockPureData,
        BlockPause.ID: BlockPause,
        BlockGroupStart.ID: BlockGroupStart,
        BlockGroupEnd.ID: BlockGroupEnd,
        BlockDescription.ID: BlockDescription,
        BlockArchiveInfo.ID: BlockArchiveInfo
    }

    def __init__(self):
        self.header = CDTHeader()
        self.blocks = []

    def compose(self):
        content = bytearray()
        content.extend(self.header.compose())
        for block in self.blocks:
            content.extend(block.compose())
        return content

    def add_block(self, content):
        if len(content) > 0:
            ID = content[0]
            content = content[1:]
            if ID in self.BLOCKS:
                b = self.BLOCKS[ID]()
                content = b.set(content)
                self.blocks.append(b)
                self.add_block(content)
            else:
                raise FormatError("unsupported block ID %s"%(hex(ID)))

    def set(self, content):
        content = self.header.set(content)
        self.blocks = []
        self.add_block(content)

    def format(self):
        """ Empty CDT with just a puse block with its default time of 3 seconds. """
        self.__init__()
        start_block = BlockPause()
        self.blocks = [start_block]

    def write(self, outputfile):
        content = self.compose()
        try:
            with open(outputfile, 'wb') as fd:
                fd.write(content)
        except IOError:
            print("[pycpc-cdt] could not write file:", outputfile)

    def read(self, inputfile):
        content = bytearray()
        chunksz = 512
        try:
            with open(inputfile, 'rb') as fd:
                bytes = fd.read(chunksz)
                while bytes:
                    content.extend(bytes)
                    bytes = fd.read(chunksz)
            self.set(content)
            return True      
        except IOError:
            print("[pycpc-cdt] could not read file:", inputfile)
        except FormatError as e:
            print("[pycpc-cdt] error in input file:", e.message)
        return False

    def _add_file(self, incontent, header, speed):
        # calculate total number of data segments of 256 bytes
        segments = []
        while len(incontent) > 0:
            segment = incontent[0:256]
            segments.append(segment)
            incontent = incontent[256:]

        while len(segments) > 0:
            """ Header """
            blocksegments = segments[0:8]
            header.block_sz = 0
            for s in blocksegments:
                header.block_sz = header.block_sz + len(s)
            header.last_block = 0x00 if len(segments) > 8 else 0xFF
            hblock = BlockTurboSpeed(speed, DEF_PAUSE_HEADER)
            hblock.data = header.compose()
            self.blocks.append(hblock)

            dblock = BlockTurboSpeed(speed, DEF_PAUSE_DATA)
            data = bytearray(b'\x16')  # sync byte for data
            """ data segments up to 8 (256 * 8 = 2K) """
            for s in blocksegments:
                # Check padding, all segments must be of 256 bytes
                if len(s) < 256: s.extend(0x00 for i in range(len(s), 256))
                crc = AUX_GET_CRC(s)
                data.extend(s)
                data.extend(crc.to_bytes(2, 'big'))  # !!! MSB first here
            data.extend(b'\xFF\xFF\xFF\xFF')  # trail
            dblock.data = data
            self.blocks.append(dblock)
            segments = segments[8:]
            header.block_id = header.block_id + 1
            header.first_block = 0x00

        endpause = BlockPause(DEF_PAUSE_FILE)
        self.blocks.append(endpause)

    def _add_raw(self, incontent, speed):
        block = BlockTurboSpeed(speed, DEF_PAUSE_FILE)
        data = bytearray(b'\x16')  # sync byte for data
        crc = AUX_GET_CRC(incontent)
        data.extend(data)
        data.extend(incontent)
        data.extend(crc.to_bytes(2, 'big'))
        data.extend(b'\xFF\xFF\xFF\xFF')
        block.data = data
        self.blocks.append(block)

    def add_file(self, incontent, header, speed):
        if header != None:
            self._add_file(incontent, header, speed)
        else:
            self._add_raw(incontent, speed)
    
    def check(self):
        self.header.check()
        for b in self.blocks: b.check()

    def dump(self):
        self.header.dump()
        print("")
        print(len(self.blocks), "BLOCKS:")
        for b in self.blocks: b.dump()


def run_read_input_file(inputfile):
    content = bytearray()
    chunksz = 65536 # 64K
    try:
        with open(inputfile, 'rb') as fd:
            bytes = fd.read(chunksz)
            while bytes:
                content.extend(bytes)
                bytes = fd.read(chunksz)
        return content      
    except IOError:
        print("[pycpc-cdt] error reading file:", inputfile)
        sys.exit(1)

def run_new(args, cdt):
    print("[pycpc-cdt] creating", args.cdtfile)
    cdt.format()
    cdt.write(args.cdtfile)
    pass

def run_check(args, cdt):
    content = run_read_input_file(args.cdtfile)
    try:
        cdt.set(content)
        cdt.check()
        print("[pycpc-cdt]", args.cdtfile, "format seems compatible")
    except FormatError as e:
        print("[pycpc-cdt] unsupported CDT format:", str(e))
        sys.exit(1)

def run_cat(args, cdt):
    run_check(args, cdt)
    cdt.dump()

def run_put_file(filein, args, cdt, header):
    run_check(args, cdt)
    content = run_read_input_file(filein)
    if len(content) > 65536:
        print("[pycpc-cdt] max input file size is 64K")
        sys.exit(1)
    if header != None:
        header.filename = args.name[0:16] if args.name != None else "UNNAMED"
        header.addr_start = args.start_addr if args.load_addr != None else 0x4000
        header.addr_load = args.load_addr if args.load_addr != None else 0x4000
    cdt.add_file(content, header, 2000 if args.speed == 1 else 1000)
    cdt.write(args.cdtfile)

def run_put_asciifile(args, cdt):
    header = DataHeader()
    header.type = DataHeader.FT_ASCII
    print("[pycpc-cdt] adding ASCII file", args.put_ascii, "to", args.cdtfile)
    run_put_file(args.put_ascii, args, cdt, header)

def run_put_binfile(args, cdt):
    header = DataHeader()
    if ".BAS" in args.put_bin.upper():
        header.type = DataHeader.FT_BAS
    else:
        header.type = DataHeader.FT_BIN
    print("[pycpc-cdt] adding BIN file", args.put_bin, "to", args.cdtfile)
    run_put_file(args.put_bin, args, cdt, header)

def run_put_rawfile(args, cdt):
    print("[pycpc-cdt] adding raw file", args.put_raw, "to", args.cdtfile)
    run_put_file(args.put_raw, args, cdt, None)

def aux_int(param):
    """
    By default, int params are converted assuming base 10.
    To allow hex values we need to 'auto' detect the base.
    """
    return int(param, 0)

def process_args():
    parser = argparse.ArgumentParser(
        prog='cdt.py',
        description='Simple tool to create and manage Amstrad CDT files'
    )
    parser.add_argument('cdtfile', help="CDT file. Used as input/output depending on the arguments used.")
    parser.add_argument('--new', action='store_true', help='Creates a new empty CDT file.')
    parser.add_argument('--check', action='store_true', help='Checks if the CDT file format is compatible with pycpc-cdt.')
    parser.add_argument('--cat', action='store_true', help='Lists in the standard output all the blocks currently present in the CDT file.')
    parser.add_argument('--put-bin', type=str, help='Adds a new binary/basic file to CDT file.')
    parser.add_argument('--put-ascii', type=str, help='Adds a new ASCII file to CDT file.')
    parser.add_argument('--put-raw', type=str, help='Adds the file directly inside a data block without any header.')
    parser.add_argument('--load-addr', type=aux_int, help='Initial address to load the file.')
    parser.add_argument('--start-addr', type=aux_int, help='Call address after loading the file.')
    parser.add_argument('--name', type=str, help='Name that will be displayed when loading the binary/ascii file.')
    parser.add_argument('--speed', type=int, default=1, help='Write speed: 0 = 1000 bauds, 1 (default) = 2000 bauds.')
    args = parser.parse_args()
    return args

def main():
    args = process_args()
    cdt = CDT()
    
    if args.new:    run_new(args, cdt)
    if args.check:  run_check(args, cdt)
    if args.cat:    run_cat(args, cdt)
    if args.put_ascii != None: run_put_asciifile(args, cdt)
    if args.put_bin != None: run_put_binfile(args, cdt)
    if args.put_raw != None: run_put_rawfile(args, cdt)
    sys.exit(0)

if __name__ == "__main__":
    main()
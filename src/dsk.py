#!/usr/bin/env python

"""
DSK.PY by Javier Garcia

Simple tool to manage Amstrad Data formated disks. Such format is defined as:
 * 180k single-sided.
 * 40 tracks of 9 512-byte sectors each.
 * Sectors numbered 0xC1 to 0xC9.
 * 64 directory entries.
 * The useable capacity is 178k.
 
INFO about the DSK file format can be read here:
http://www.benchmarko.de/cpcemu/cpcdoc/chapter/cpcdoc7_e.html#I_FILE_STRUCTURE
https://www.cpcwiki.eu/index.php/Format:DSK_disk_image_file_format
https://sinclair.wiki.zxnet.co.uk/wiki/DSK_format

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation in its version 3.

This program is distributed in the hope that it will be useful
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys
import os
import argparse
import math

ADDR_EXE = 0
ADDR_LOAD = 0

AMSDOS_BAS_TYPE = 0
AMSDOS_PROTECTED_TYPE = 1
AMSDOS_BIN_TYPE = 2

CPM_DELETED = 0xE5
CPM_TEXT_EOF = 0x1A
CPM_MIN_SECTOR = 0xC1       # only in data format
CPM_MAX_SECTOR = 0xC9       # only in data format
CPM_PAGE_BYTES = 128        # page of data is 128 bytes in CP/M
CPM_CLUSTER_SECTORS = 2     # 2 sectors (1K) form a data block or 'cluster'
CPM_CLUSTER_BYTES = 1024
CPM_CLUSTER_PAGES = 8

# 9 sectors * 512 bytes/sector + header of 256 bytes
DEF_TRACK_SZ = 256 + 512 * 9
DEF_SIDES = 1
DEF_TRACKS = 40
DEF_SECTORS = 9

class FormatError(Exception):
    """
    Raised when procesing a file and its format is not the expected one.
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class DiskHeader:
    """
    Encapsulates the header of a DSK file. It compromises the first 256 bytes.
    """
    def __init__(self, tracks, sztrack, sides):
        self.title = b'MV - CPCEMU Disk-File\r\nDisk-Info\r\n'
        self.tracks = tracks
        self.sztrack = sztrack
        self.sides = sides

    def compose(self):
        # Total size of 256 bytes
        header = bytearray()
        header.extend(self.title)
        header.extend(0x00 for i in range(0, 48-len(header)))
        header.extend(self.tracks.to_bytes(1, 'little'))
        header.extend(self.sides.to_bytes(1, 'little'))
        header.extend(self.sztrack.to_bytes(2, 'little'))
        header.extend(0x00 for i in range(0, 204))
        return header

    def set(self, content):
        if len(content) < 256:
            raise FormatError("header size is less than 256 bytes")
        self.title = content[0:48]
        self.tracks = content[48]
        self.sides = content[49]
        self.sztrack = int.from_bytes(content[50:52], 'little')
        return content[256:]
    
    def check(self, tracks, sztrack, sides):
        if b'MV - CPCEMU' not in self.title:
            raise FormatError("disk header title doesn't contain 'MV - CPCEMU' text")
        if self.sides != sides:
            raise FormatError("header number of sides (%d) differs from expected values (%d)"%(self.sides, sides))
        if self.tracks < tracks:
            raise FormatError("header number of tracks (%d) differs from expected value (%d)"%(self.tracks, tracks))
        if self.sztrack != sztrack:
            raise FormatError("header track size (%d) differs from expected value (%d)"%(self.tracks, tracks))

    def dump(self):
        print("HEADER:")
        print(" title:", self.title)
        print(" tracks:", self.tracks)
        print(" sides:", self.sides)
        print(" track total size in bytes:", self.sztrack)
        print("")

class TrackSectorInfo:
    """
    Encapsulates de sector info section contained in track headers. 8 bytes of size.
    """
    def __init__(self, sector, track, side, basetrack):
        self.C = track
        self.H = side
        self.R = basetrack + sector
        self.N = 2 # 0x02
        # State registers
        self.ST1 = 0 # 0x00
        self.ST2 = 0 # 0x00
        
    def compose(self):
        content = bytearray()
        content.extend(self.C.to_bytes(1, 'little'))
        content.extend(self.H.to_bytes(1, 'little'))
        content.extend(self.R.to_bytes(1, 'little'))
        content.extend(self.N.to_bytes(1, 'little'))
        # status registers
        content.extend(self.ST1.to_bytes(1, 'little'))
        content.extend(self.ST2.to_bytes(1, 'little'))
        # not used according to the standar spec
        content.extend(b'\x00\x00')
        return content

    def set(self, content):
        if len(content) < 8:
            raise FormatError("there is a sector info section of less than 8 bytes")
        self.C = content[0]
        self.H = content[1]
        self.R = content[2]
        self.N = content[3]
        self.ST1 = content[4]
        self.ST2 = content[5]
        return content[8:]

    def check(self, track):
        if self.C != track:
            raise FormatError("unexpected sector info track number (%d), %d was expected"%(self.C, track))
        if self.N != 2:
            raise FormatError("sector info N value (%s) differs from expected value (0x02)"%(hex(self.N)))
        if self.H != 0:
            raise FormatError("sector info H value (%s) differs from expected value (0x00)"%(hex(self.H)))
        if self.R < CPM_MIN_SECTOR or self.R > CPM_MAX_SECTOR:
            raise FormatError("sector R value (%s) differs from expected value C1-C9"%(hex(self.R)))

    def dump(self):
        print(hex(self.R), end = ' ')

class TrackHeader:
    """
    Encapsulates the track header. Size is 256 bytes. By default, expected number
    of sectors is 9. Sector's data should follow the same orden than the items in
    the sectors info list contained here. Sectors are not necessarily consecutive. 
    Indeed in many cases they are interleaved, which is the order followed here
    by default: C1, C6, C2, C7, C3, C8, C4, C8, C5 ...
    All track header sizes are 256 bytes.
    """
    def __init__(self, track, sectors, basetrack, side):
        self.title = b'Track-Info\r\n'
        self.track = track
        self.sectors = sectors
        self.side = side
        # Sector size parameter (1=256, 2=512, 3=1024 ...)
        self.szsector = 2 # 0x02
        self.gap3 = 78    # 0x4E
        self.filler = CPM_DELETED  # 0xE5
        # interleaved sectors
        sec_first = 0
        sec_second = 5
        addedsectors = 0
        self.sectors_info = []
        while addedsectors < sectors:
            self.sectors_info.append(TrackSectorInfo(sec_first, track, side, basetrack))
            sec_first = sec_first + 1
            addedsectors = addedsectors + 1
            if (addedsectors < self.sectors):
                self.sectors_info.append(TrackSectorInfo(sec_second, track, side, basetrack))
                sec_second = sec_second + 1
                addedsectors = addedsectors + 1

    def compose(self):
        # 256 bytes in total, data always starts at 0x100
        # no matter number of sectors
        header = bytearray()
        header.extend(self.title)
        header.extend([0x00 for i in range(0,4)]) # unused
        header.extend(self.track.to_bytes(1, 'little'))
        header.extend(self.side.to_bytes(1, 'little'))
        header.extend(b'\x00\x00') # unused
        header.extend(self.szsector.to_bytes(1, 'little')) 
        header.extend(self.sectors.to_bytes(1, 'little'))
        header.extend(self.gap3.to_bytes(1, 'little'))
        header.extend(self.filler.to_bytes(1, 'little'))
        # sectors info: secuence is 0, 4, 1, 5, 2, 6, 3, 7, 8 ...
        for s in self.sectors_info:
            header.extend(s.compose())
        header.extend(0x00 for i in range(0, 256-len(header)))
        return header

    def set(self, sectors, content):
        if len(content) < 256:
            raise FormatError("track header size is less than 256 bytes")
        self.title = content[0:12]
        self.track = content[16]
        self.side = content[17]
        self.szsector = content[20]
        self.sectors = content[21]
        if self.sectors != sectors:
            raise FormatError("expected number of sectors per track is 9, not %d"%(self.sectors))
        # keep our GAP3 and Filler byte values
        sectorinfo = content[24:]
        for i in range(0, DEF_SECTORS):
            sectorinfo = self.sectors_info[i].set(sectorinfo)
        return content[256:]

    def check(self):
        if self.title != b'Track-Info\r\n':
            raise FormatError("unexpected track header title")
        if self.side != 0:
            raise FormatError("track side number should be 0, %d was found"%(self.side))
        if self.sectors != DEF_SECTORS:
            raise FormatError("track number of sectors (%d) differes from expected value (%d)"%(self.sectors, DEF_SECTORS))
        if self.szsector != 2:
            raise FormatError("track sector size code (%d) differs from expected value (2)"%(self.szsector))
        if self.gap3 != 78:
            raise FormatError("track GAP#3 field value (%d) differs from expected value (78)"%(self.gap3))
        if self.filler != CPM_DELETED:
            raise FormatError("track FILL field value (%d) differs from expected value (%d)"%(self.filler, CPM_DELETED))
        for i in range(0, DEF_SECTORS):
           self.sectors_info[i].check(self.track)

    def dump(self):
        print("TRACK %02d"%(self.track), end = ' ')
        print("side:", self.side, "sectors:", end=' ')
        for i in range(0, DEF_SECTORS):
           self.sectors_info[i].dump()
        print("")

class TrackData:
    """
    Encapsulates the track data area. Expected size is 512 bytes per sector.
    """
    def __init__(self, sectors, filler):
        self.data = bytearray()
        for i in range(0, 512*sectors): self.data.extend(filler.to_bytes(1, 'little'))
        self.sectors = sectors

    def compose(self):
        return self.data

    def set(self, sectors, content):
        self.sectors = sectors
        datasz = 512 * sectors
        if len(content) < datasz:
            raise FormatError("track size area is less than 512 bytes x %d sectors", sectors)
        self.data = content[0:datasz]
        return content[datasz:]
    
    def check(self):
        datasz = 512 * DEF_SECTORS
        if len(self.data) != datasz:
            raise FormatError("track data size (%d) differes from expected value (%d)"% (len(self.data, datasz)))

    def get_sector_data(self, sector, dbytes = 512):
        return self.data[512*sector: 512*sector + dbytes]
    
    def set_sector_data(self, sector, data):
        # be sure data is 512 bytes
        if len(data) < 512:
            data.extend(0x00 for i in range(0, 512 - len(data)))
        else:
            data = data[0:512]
        newdata = bytearray()
        if sector > 0:
            newdata.extend(self.data[0:512*sector])
        newdata.extend(data)
        if sector < 8:
            newdata.extend(self.data[512*(sector+1):])
        self.data = newdata

class Track:
    """
    Encapsulates one track of a DSK file. Each track contains one head and one data zone.
    - Head is 256 bytes
    - Data zone is 512 * sectors bytes
    """
    def __init__(self, track, sectors, basetrack, side = 0):
        self.header = TrackHeader(track, sectors, basetrack, side)
        self.data = TrackData(sectors, self.header.filler)
        self.side = side
        self.basetrack = basetrack
        self.sectors = sectors
        self.track = track

    def compose(self):
        content = bytearray()
        content.extend(self.header.compose())
        content.extend(self.data.compose())
        return content

    def set(self, sectors, content):
        self.sectors = sectors
        content = self.header.set(sectors, content)
        self.track = self.header.track
        self.side = self.header.side
        content = self.data.set(sectors, content)
        return content
    
    def check(self):
        if self.side != 0:
            raise FormatError("track side number should be 0, %d was found"%(self.side))
        self.header.check()
        self.data.check()

    def dump(self):
        self.header.dump()

    def get_sector_data(self, sectorid, dbytes = 512):
        for i in range(0, len(self.header.sectors_info)):
            if self.header.sectors_info[i].R == sectorid:
                return self.data.get_sector_data(i, dbytes)

    def set_sector_data(self, sectorid, content):
        for i in range(0, len(self.header.sectors_info)):
            if self.header.sectors_info[i].R == sectorid:
                self.data.set_sector_data(i, content)

class Disk:

    def __init__(self, tracks = DEF_TRACKS, sectors = DEF_SECTORS, sztrack = DEF_TRACK_SZ , sides = DEF_SIDES):
        self.ntracks = tracks
        self.nsectors = sectors
        self.nsides = sides
        self.sztrack = sztrack
        self.header = DiskHeader(self.ntracks, self.sztrack, self.nsides)
        self.tracks = [Track(i, self.nsectors, CPM_MIN_SECTOR) for i in range(0, self.ntracks)]

    def compose(self):
        disk = bytearray()
        disk.extend(self.header.compose())
        for t in self.tracks:
            disk.extend(t.compose())
        return disk

    def set(self, content):
        content = self.header.set(content)
        self.ntracks = self.header.tracks
        self.nsides = self.header.sides
        self.sztrack = self.sztrack
        # default number of sectors
        if self.ntracks < len(self.tracks):
            raise FormatError("unexpected number of tracks (%d vs %d)"%(self.ntracks, len(self.tracks)))
        self.nsectors = 9
        for t in self.tracks:
            content = t.set(self.nsectors, content)

    def format(self):
        self.__init__()

    def write(self, outputfile):
        content = self.compose()
        try:
            with open(outputfile, 'wb') as fd:
                fd.write(content)
        except IOError:
            print("[dsk] could not write file:", outputfile)

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
            print("[dsk] could not read file:", inputfile)
        except FormatError as e:
            print("[dsk] error in input file:", e.message)
        return False

    def check(self):
        if self.ntracks < len(self.tracks):
            raise FormatError("number of tracks (%d) differs from expected values (%d)"%(self.ntracks, len(self.tracks)))
        self.header.check(DEF_TRACKS, DEF_TRACK_SZ, DEF_SIDES)
        for t in self.tracks:
            t.check()

    def dump(self):
        self.header.dump()
        for t in self.tracks:
            t.dump()

    def get_dirtable(self):
        dir = DirTable()
        base = CPM_MIN_SECTOR
        content = bytearray()
        for i in range(0, 4):
            content.extend(self.tracks[0].get_sector_data(base + i))
        dir.set(content)
        return dir

    def set_dirtable(self, dirtable):
        content = dirtable.compose()
        for i in range(0, 4):
            data = content[0:512]
            self.tracks[0].set_sector_data(CPM_MIN_SECTOR + i, data)
            content = content[512:]

    def get_content(self, track, sector, dbytes):
        """ Returns dbytes of data from the specified track and sector """
        sectorid = CPM_MIN_SECTOR + sector
        return self.tracks[track].get_sector_data(sectorid, dbytes)

    def add_content(self, sectors, content):
        for (t, s) in sectors:
            data = content[0:512]
            # padding
            data.extend(0x00 for i in range(len(data), 512))
            self.tracks[t].set_sector_data(CPM_MIN_SECTOR + s, data)
            content = content[512:]

class DirEntry:
    """
    Encapsulates a CP/M directory entry. Size is 32 bytes. It keeps up to 16 clusters
    pointing to 'blocks' of data (2 consecutive sectors so 1K). As a result, each entry
    can addres up to 16k of data. Pages indicate the number of clusters in use.  
    """
    def __init__(self, num):
        self.entry = num
        self.status = CPM_DELETED   # usually user ID (0-15) or deleted 0xE5
        self.name = bytearray([CPM_DELETED for i in range(0,8)]) # spaces
        self.ext = bytearray([CPM_DELETED for i in range(0,3)]) # spaces
        self.extend = CPM_DELETED   # 0-31 (large files can spread through several entries)
        self.pages = CPM_DELETED
        self.clusters = bytearray([CPM_DELETED for i in range(0,16)])

    def compose(self):
        entry = bytearray()
        if self.status == CPM_DELETED:
            entry.extend(CPM_DELETED for i in range(0, 32))
        else:
            entry.extend(self.status.to_bytes(1, 'little'))
            entry.extend(self.name)
            entry.extend(self.ext)
            entry.extend(self.extend.to_bytes(1, 'little'))
            entry.extend(b'\x00\x00')
            entry.extend(self.pages.to_bytes(1, 'little'))
            entry.extend(self.clusters)
        return entry

    def to_sectors(self, iblock, npages = 0):
        """
        Returns the list of (track, sector, bytes) pointed by data iblock and containing npages of data (0-8).
        If npages == 0 then all pages assigned to the specified block are used
        """
        sectors = []
        offset = 0
        if npages == 0:
            npages = self.pages
            for i in range(0, iblock): npages = npages - CPM_CLUSTER_PAGES
            npages = min(CPM_CLUSTER_PAGES, npages)
        while npages > 0:
            sector = (self.clusters[iblock] * 2 + offset)
            track = int(sector / DEF_SECTORS)
            sector = sector % DEF_SECTORS
            dbytes = 512 if npages > 3 else npages * CPM_PAGE_BYTES
            sectors.append((track, sector, dbytes))
            npages = npages - 4
            offset = 1
        return sectors
    
    def get_clusters(self):
        """ Returns number of valid used clusters (1-16) according to current number of data pages """
        return math.ceil(self.pages / CPM_CLUSTER_PAGES)

    def get_filename(self):
        filename = str.strip(self.name.decode('utf-8')) + '.'
        return filename + str.strip(self.ext.decode('utf-8'))

    def set(self, content):
        self.status = content[0]
        self.name = content[1:9]
        self.ext = content[9:12]
        self.extend = content[12]
        # 13 and 14 are unused
        self.pages = content[15]
        self.clusters = content[16:32]
        return content[32:]

    def dump(self):
        print(self.entry, end = ': ')
        if self.status == CPM_DELETED:
            print("DELETED/NOT USED")
        else:
            print(self.name.decode('utf-8') + '.' + self.ext.decode('utf-8'), end = '  [ ')
            print("st:", self.status, "extend:", self.extend, "data pages:", self.pages, ']')

class DirTable:
    """
    Amstrad disks use CP/M format. A directory table contains 64 entries of
    32 bytes each, 2K total. In data formated disk, the table is located in track 0,
    sectors C1-C4 (16 entries in each sector)
    """
    def __init__(self):
        self.entries = [DirEntry(i) for i in range(0, 64)]

    def compose(self):
        content = bytearray()
        for i in range(0, 64):
            content.extend(self.entries[i].compose())
        return content

    def set(self, content):
        for i in range(0, 64):
            content = self.entries[i].set(content)

    def dump(self):
        for e in self.entries:
            if e.status != CPM_DELETED:
                e.dump()

    def can_allocate(self, filebytes):
        """ 
        Checks if there are enough consecutive free dir entries to acoomodate a file of the given size.
        It returns the first entry to allocate the file or -1 if there are not enough free entries.
        """
        numentries = math.ceil(filebytes / (16 * 1024)) # each entry points to 16K of data
        freeentries = 0
        startentry = 0
        for i in range(0, len(self.entries)):
            entry = self.entries[i]
            if entry.status == CPM_DELETED:
                freeentries = freeentries + 1
                if freeentries >= numentries:
                    break
            else:
                freeentries = 0
                startentry = i + 1
        if freeentries < numentries: startentry = -1
        return startentry
 
    def to_file_sectors(self, ientry):
        """ Returns a list of (track, sector, bytes) for the file pointed by the directory entry """
        entry = self.entries[ientry]
        clusters = entry.get_clusters()
        sectors = []
        totpages = entry.pages
        for b in range(0, clusters):
            sectors = sectors + entry.to_sectors(b)
        if clusters == 16 and ientry < len(self.entries) - 2:
            next_entry = self.entries[ientry + 1]
            if next_entry.status != CPM_DELETED and next_entry.extend > 0:
                # This file is assigned to several directory entries
                # it happens with files bigger than 16k
                totpages = totpages + next_entry.pages
                sectors = sectors + self.to_file_sectors(ientry + 1)
        return sectors, totpages

    def write_entries(self, ientry, filename, fbytes):
        """
        Returns the list of (track, sector) consumed by the file.
        This assumes that ientry was obtained with a call to can_allocate and
        no other write operations where performed since
        """
        disk_clusters, _ = self.get_disk_clusters()
        file_sectors = []
        filepages = math.ceil(fbytes/CPM_PAGE_BYTES)
        filecomp = os.path.basename(filename).split('.')
        fext = bytearray(b'\x20\x20\x20') if len(filecomp) == 1 else bytearray(filecomp[1][0:3].upper().encode('utf-8'))
        fname = bytearray(filecomp[0][0:8].upper().encode('utf-8'))
        fext.extend(0x20 for i in range(3 - len(fext)))
        fname.extend(0x20 for i in range(8 - len(fname)))
        extend = 0
        while filepages > 0:
            e = self.entries[ientry]
            e.status = 0
            e.name = fname
            e.ext = fext
            e.pages = min(128, filepages)
            eclusters = math.ceil(e.pages/CPM_CLUSTER_PAGES)
            cluster = 0
            for ec in range(0, 16):
                if ec < eclusters:
                    # find next free cluster
                    while cluster < len(disk_clusters) and not disk_clusters[cluster]:
                        cluster = cluster + 1
                    # no free cluster
                    if cluster == len(disk_clusters):
                        return []
                    e.clusters[ec] = cluster
                    disk_clusters[cluster] = False
                    for s in range(cluster * CPM_CLUSTER_SECTORS, (cluster+1) * CPM_CLUSTER_SECTORS):
                        file_sectors.append((math.floor(s/DEF_SECTORS), s%DEF_SECTORS))
                else:
                    e.clusters[ec] = 0x00
            e.extend = extend
            extend = extend + 1
            filepages = filepages - e.pages
            ientry = ientry + 1
        return file_sectors


    def get_disk_clusters(self):
        """
        Returns a list of all avaliable clusters indicating if they are
        free (True) or used (False) and the total remaining free space in KB
        """
        clusters = [True for i in range(0, len(self.entries) * 16)]
        freekb = int((DEF_SECTORS * DEF_TRACKS * 512) / 1024)
        # dir table space
        clusters[0] = clusters[1] = False
        freekb = freekb - 2
        for e in self.entries:
            if e.status != CPM_DELETED:
                valid_blocks = math.ceil(e.pages / CPM_CLUSTER_PAGES) 
                for i in range(0, valid_blocks):
                    clusters[e.clusters[i]] = False
                    freekb = freekb - 1
        return clusters, freekb

class AmsdosHead:
    """
    In AMSDOS it is possible to store files in two ways: headerless and with a header.
    Headerless files are often files which were created with OPENOUT and SAVE"filename",a.
    One example is ASCII files. Programs normally have a file header, which consist of 128 bytes.
    """
    def __init__(self):
        self.user = 0           # user number (0-15), 0xE5 for deleted entries
        self.file_name = bytearray(0x20 for i in range(0,8)) # unused chars filled with spaces
        self.file_ext = bytearray(0x20 for i in range(0,3))  # unused chars filled with spaces
        self.file_type = AMSDOS_BIN_TYPE
        self.file_size = 0
        self.block_num = 0      # TAPE only
        self.block_last = 0     # TAPE only
        self.block_fist = 0xFF  # Only used for output files. Set by default to FF
        self.addr_data = 0      # Data area (2KB buffer) location
        self.addr_load = 0      # Memory address where file must be loaded
        self.addr_entry = 0     # Entry point
        self.real_size = 0      # copy of file_size, 3 bytes. Not really used
        self.custom = bytearray(0x00 for i in range(0,36)) # unused but affects checksum
        self.checksum = 0       # 2 bytes. Sum of first 66 bytes

    def set(self, content):
        if len(content) < 128:
            raise FormatError("AMSDOS header size should be 128 bytes")
        self.user = content[0]
        self.file_name = content[1:9]
        self.file_ext = content[9:12]
        self.block_num = content[16]
        self.block_last = content[17]
        self.file_type = content[18]
        self.addr_data = int.from_bytes(content[19:21], 'little')
        self.addr_load = int.from_bytes(content[21:23], 'little')
        self.block_fist = content[23]
        self.file_size = int.from_bytes(content[24:26], 'little')
        self.addr_entry = int.from_bytes(content[26:28], 'little')
        self.custom = content[28:64]
        self.real_size = int.from_bytes(content[64:67], 'little')
        self.checksum = int.from_bytes(content[67:69], 'little')
        return content[128:]

    def compose(self):
        header = bytearray()
        header.extend(self.user.to_bytes(1, 'little'))
        header.extend(self.file_name)
        header.extend(self.file_ext)
        header.extend(b'\x00\x00\x00\x00')
        header.extend(self.block_num.to_bytes(1, 'little'))
        header.extend(self.block_last.to_bytes(1, 'little'))
        header.extend(self.file_type.to_bytes(1, 'little'))
        header.extend(self.addr_data.to_bytes(2, 'little'))
        header.extend(self.addr_load.to_bytes(2, 'little'))
        header.extend(self.block_fist.to_bytes(1, 'little'))
        header.extend(self.file_size.to_bytes(2, 'little'))
        header.extend(self.addr_entry.to_bytes(2, 'little'))
        header.extend(self.custom) # unused area but affects checksum
        header.extend(self.real_size.to_bytes(3, 'little')) # a copy not used
        header.extend(self.checksum.to_bytes(2, 'little'))
        # free to use area and padding
        header.extend(0x00 for i in range(0, 128-len(header)))
        return header

    def calculate_checksum(self):
        header = self.compose()
        checksum = 0
        for i in range(0, 67): checksum = checksum + header[i]
        return checksum

    def update_checksum(self):
        self.checksum = self.calculate_checksum()

    def is_valid_header(self):
        # We need to double check that not all bytes are 0x00 or we will
        # believe that an empty area is a valid header
        data = self.compose()
        accum = 0x00
        for b in data: accum = accum | b
        if accum == 0:
            return False
        checksum = self.calculate_checksum()
        return checksum == self.checksum
    
    def build(self, file, filesz):
        filecomp = os.path.basename(file).split('.')
        fext = bytearray(b'\x20\x20\x20') if len(filecomp) == 1 else bytearray(filecomp[1][0:3].upper().encode('utf-8'))
        fname = bytearray(filecomp[0][0:8].upper().encode('utf-8'))
        self.__init__()
        fext.extend(0x20 for i in range(3 - len(fext)))
        fname.extend(0x20 for i in range(8 - len(fname)))
        self.file_name = fname
        self.file_ext = fext
        self.file_type = AMSDOS_BIN_TYPE if fext != b'BAS' else AMSDOS_BAS_TYPE
        self.file_size = filesz
        self.real_size = filesz
        self.update_checksum()

    def dump(self):
        print("[dsk] AMSDOS header:")
        print(f"  File: {self.file_name.decode('utf-8') + '.' + self.file_ext.decode('utf-8')}")
        print(f"  File type: {self.file_type} File size: {self.file_size} User ID: {self.user}")
        print(f"  Load address: {hex(self.addr_load)} Exec address: {hex(self.addr_entry)}")
        print(f"  Data address: {hex(self.addr_data)} Checksum: {self.checksum}")

def run_new(args, disk):
    print("[dsk] creating", args.dskfile)
    disk.write(args.dskfile)

def run_check(args,disk):
    if not disk.read(args.dskfile):
            sys.exit(1)
    try:
        disk.check()
    except FormatError as e:
        print("[dsk] unsupported DSK format:", e.message)
        sys.exit(1)

def run_dump(args, disk):
    run_check(args, disk)
    print("[dsk] dumping information for file", args.dskfile)
    disk.dump()

def run_cat(args, disk):
    run_check(args, disk)
    print("[dsk] listing", args.dskfile, "content:")
    dirtable = disk.get_dirtable()
    dirtable.dump()

def run_check_direntry(disk, ientry):
    dirtable = disk.get_dirtable()
    entry = dirtable.entries[ientry]
    if entry.status == CPM_DELETED:
        print("[dsk] specified directory entry does not contain a file")
        sys.exit(1)
    if entry.extend > 0:
        print("[dsk] specified directory entry is not a file starting entry")
        sys.exit(1)
    return dirtable, entry

def run_dump_header(args, disk):
    run_check(args, disk)
    _ ,entry = run_check_direntry(disk, args.header)
    # header is 128 byes so we get the first page of the first data block
    [(t, s, b)] = entry.to_sectors(0, 1)
    content = disk.get_content(t, s, b)
    header = AmsdosHead()
    header.set(content)
    print("[dsk] header located at track:", t, "sector:", s)
    if not header.is_valid_header():
        print("but it doesn't seem to contain a valid AMSDOS header:")
        for byte in content[0:69]: print(hex(byte), end=' ')
        sys.exit(1)
    header.dump()

def run_get_file(args, disk):
    run_check(args, disk)
    dirtable, entry = run_check_direntry(disk, args.get)
    filename = entry.get_filename()
    sectors, npages = dirtable.to_file_sectors(args.get)
    realsz = npages * CPM_PAGE_BYTES
    data = bytearray()
    for (t, s, b) in sectors:
        data.extend(disk.get_content(t, s, b))
    head = AmsdosHead()
    head.set(data[0:128])
    if head.is_valid_header():
        realsz = head.file_size + 128
        if args.no_header:
            print("[dsk] removing ASMDOS header from", filename)
            data = data[128:]
            realsz = realsz - 128
    try:
        data = data[0:realsz]
        with open(filename, 'wb') as fd:
            fd.write(data)
    except IOError:
        print("[dsk] error trying to write file:", filename)
    print("[dsk] file", filename, "was extracted:", npages, "pages of data,",len(data), "bytes written")

def run_read_input_file(inputfile):
    content = bytearray()
    chunksz = 128 * 1024    # 128K is the max disk size
    filemaxsz = 64 * 1024   # max file size is 64K
    try:
        with open(inputfile, 'rb') as fd:
            bytes = fd.read(chunksz)
            while bytes:
                content.extend(bytes)
                bytes = fd.read(chunksz)
        if len(content) > filemaxsz:
            print("[dsk] files cannot be bigger than 64K")
            sys.exit(1)
        return content      
    except IOError:
        print("[dsk] error reading file:", inputfile)
        sys.exit(1)

def run_read_mapfile(mapfile):
    print("[dsk] reading map file", mapfile)
    try:
        with open(mapfile, 'r') as fd:
            content = str.join('', fd.readlines())
            return eval(content)
    except IOError:
        print("[dsk] error reading file:", mapfile)
        sys.exit(1)

def run_get_start(startaddr, mapfile):
    try:
        addr = aux_int(startaddr)
        return addr
    except:
        startaddr = startaddr.upper()
        if startaddr in mapfile:
            return mapfile[startaddr][0]
        print("[dsk] invalid start address value")
        sys.exit(1)

def run_put_file(infile, dskfile, disk, content):
    dirtable = disk.get_dirtable()
    ientry = dirtable.can_allocate(len(content))
    if ientry == -1:
        print("[dsk] disk lacks enough free space to include the new file")
        sys.exit(1)
    sectors = dirtable.write_entries(ientry, infile, len(content))
    disk.set_dirtable(dirtable)
    disk.add_content(sectors, content)
    disk.write(dskfile)
    print("[dsk] file added successfuly")

def run_put_asciifile(args, disk):
    content = run_read_input_file(args.put_ascii)
    print("[dsk] adding ASCII file", args.put_ascii, "to", args.dskfile)
    run_check(args, disk)
    # ASCII files always go without AMSDOS header. Additionaly, CPM 2.2 uses a 
    # special character to indicate end of file. Lets check if the file already
    # includes it.
    if content[len(content)-1] != CPM_TEXT_EOF and len(content) % CPM_PAGE_BYTES != 0:
        content.extend(CPM_TEXT_EOF.to_bytes(1, 'little'))
    run_put_file(args.put_ascii, args.dskfile, disk, content)

def run_put_binfile(args, disk, infile, addheader):
    content = run_read_input_file(infile)
    print("[dsk] adding binary file",
          infile, "to", args.dskfile,
          '' if addheader else 'without adding an AMSDOS header')
    run_check(args, disk)
    header = AmsdosHead()
    if len(content) > 128:
        header.set(content[0:128])
        if header.is_valid_header() and addheader:
            print('[dsk] AMSDOS header found, deleting it before generating a new one')
            content = content[128:]
    if addheader:
        mapfile = {}
        header.build(infile, len(content))
        if args.map_file != None: mapfile = run_read_mapfile(args.map_file)
        if args.load_addr != None: header.addr_load = args.load_addr
        if args.start_addr != None: header.addr_entry = run_get_start(args.start_addr, mapfile)
        header.update_checksum()
        content = bytearray(header.compose() + content)
    run_put_file(infile, args.dskfile, disk, content)

def aux_int(param):
    """
    By default, int params are converted assuming base 10.
    To allow hex values we need to 'auto' detect the base.
    """
    return int(param, 0)

def process_args():
    parser = argparse.ArgumentParser(
        prog='dsk.py',
        description='Simple tool to create and manage Amstrad sigle side DSK files'
    )
    parser.add_argument('dskfile', help="DSK file. Used as input/output depending on the arguments used.")
    parser.add_argument('--new', action='store_true', help='Creates a new empty DSK file.')
    parser.add_argument('--check', action='store_true', help='Checks if the DSK file format is compatible with dsk.')
    parser.add_argument('--dump', action='store_true', help='Prints DSK file format information on the standard ouput.')
    parser.add_argument('--cat', action='store_true', help='Lists in the standard output the DSK file content.')
    parser.add_argument('--header', type=int, help='Prints AMSDOS header for indicated file entry starting at 0.')
    parser.add_argument('--get', type=int, help='Extracts file pointed by the indicated entry. Use --no-header to remove AMSDOS header.')
    parser.add_argument('--put-bin', type=str, help='Adds a new binary file to DSK file creating and appending an extra AMSDOS header.')
    parser.add_argument('--put-raw', type=str, help='Adds a new binary file to DSK file without creating an extra AMSDOS header.')
    parser.add_argument('--put-ascii', type=str, help='Adds a new ASCII file to DSK file. The file should not include an AMSDOS header.')
    parser.add_argument('--map-file', type=str, help='Imports a map file with symbol names and addresses that can be referenced in the --start-addr option')
    parser.add_argument('--load-addr', type=aux_int, default=0x4000, help='Initial address to load the file (default 0x4000). Only used in binary files with appended AMSDOS headers.')
    parser.add_argument('--start-addr',
                        type=str,
                        default="0x4000",
                        help='Call address (by default 0x4000).' +
                             'the binary file must include an AMSDOS header. If a map file is imported a symbol name can be used')

    args = parser.parse_args()
    return args

def main():
    args = process_args()
    disk = Disk()
    
    if args.new:    run_new(args, disk)
    if args.check:  run_check(args, disk)
    if args.dump:   run_dump(args, disk)
    if args.cat:    run_cat(args, disk)
    if args.header != None: run_dump_header(args, disk)
    if args.get != None: run_get_file(args, disk)
    if args.put_ascii != None: run_put_asciifile(args, disk)
    if args.put_bin != None: run_put_binfile(args, disk, args.put_bin, True)
    if args.put_raw != None: run_put_binfile(args, disk, args.put_raw, False)
    sys.exit(0)

if __name__ == "__main__":
    main()
import os
import struct
import mmap


class VMSN(str):
    def __init__(self, name):
        self.mem_fd = open(name+".vmem", "r+")
        self.mem_size = os.fstat(self.mem_fd.fileno()).st_size
        self.mem_data = mmap.mmap(self.mem_fd.fileno(), self.mem_size)

        self.vmsn_fd = open(name+".vmsn", "r+")
        self.vmsn_size = os.fstat(self.vmsn_fd.fileno()).st_size
        self.vmsn_data = mmap.mmap(self.vmsn_fd.fileno(), self.vmsn_size)


        #WARNING !!! TODO !!!!! This is a PoC !
        #This is crappy, I know but ok for now !
        #We need to parse!!!
        #XXX THOSE OFFSETS WILL NOT WORK FOR YOUR VMSN !!!
        CPU_INFO_INDEX = (0x713C, 43, 1123) #CPU0 in my case
        CPU_INFO_INDEX = (0x8CC0, 43, 1100) #CPU1 in my case

        self.vmsn_fd.seek(CPU_INFO_INDEX[0], 0)
        Name = self.vmsn_fd.read(3)
        Cpuid = struct.unpack("B", self.vmsn_fd.read(1))
        Null = self.vmsn_fd.read(3)
        if Name != "rip":
            print "Name %s" % list(Name)
            print "Failed !"
            return False

        self.rip = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        print "rip 0x%x" % (self.rip)

        self.vmsn_fd.seek(CPU_INFO_INDEX[0]+CPU_INFO_INDEX[1], 0)
        Name = self.vmsn_fd.read(6)
        Cpuid = struct.unpack("B", self.vmsn_fd.read(1))
        Null = self.vmsn_fd.read(5)
        if Name != "gpregs":
            print "Name gpregs %s" % list(Name)
            print "Failed !"
            return False

        self.rax = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rbx = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rcx = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rdx = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rdi = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rsi = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rsp = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rbp = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r8 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r9 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r10 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r11 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r12 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r13 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r14 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.r15 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.cs = 0x0
        self.fs = 0x0
        self.gs = 0x0

        self.vmsn_fd.seek(CPU_INFO_INDEX[0]+CPU_INFO_INDEX[2], 0)
        Name = self.vmsn_fd.read(4)
        Cpuid = struct.unpack("B", self.vmsn_fd.read(1))
        Null = self.vmsn_fd.read(5)
        if Name != "CR64":
            print "Name %s" % list(Name)
            print "Failed !"
            return False

        struct.unpack("Q", self.vmsn_fd.read(8))[0]
        struct.unpack("Q", self.vmsn_fd.read(8))[0]
        struct.unpack("Q", self.vmsn_fd.read(8))[0]
        struct.unpack("Q", self.vmsn_fd.read(8))[0]
        struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.cr3 = struct.unpack("Q", self.vmsn_fd.read(8))[0]
        self.rflags = 0x0000000000010246

    def GetCpuCount(self):
        return 1

    def Pause(self):
        return True

    def UnsetAllBreakpoint(self):
        return True

    def SetBreakpoint(self, a0, a1, a2, a3, a4, a5, a6):
        return 0

    def ReadyPhysicalMemory(self, address, size):
        return self.mem_data[address:address+size]

    def ReadPhysical64(self, address):
        data = self.mem_data[address:address+8]
        return struct.unpack("Q", data)[0]

    def V2P(self, address):
        _4K = 4*1024
        _2M = 2*1024*1024
        PML4E_index =  (address & 0x0000FF8000000000) >> (9 + 9 + 9 + 12)
        PDPE_index = (address & 0x0000007FC0000000) >> (9 + 9 + 12);
        PDE_index = (address & 0x000000003FE00000) >> (9 + 12);
        PTE_index = (address & 0x00000000001FF000) >> (12);
        P_offset = (address & 0x0000000000000FFF);
        CR3 = self.cr3 & 0xFFFFFFFFFFFFF000

        PDPE_base = self.ReadPhysical64(CR3 + (PML4E_index * 8)) & 0x0000FFFFFFFFF000;
        if ((PDPE_base == 0) or (PDPE_base > (self.mem_size - _4K))):
            return None;
        tmp = self.ReadPhysical64(PDPE_base + (PDPE_index * 8));
        if (tmp & 0x80): # This pas is a huge one (1G) !
            print "TODO !!  HUGE !!!";
            return None;
        PDE_base = tmp & 0x0000FFFFFFFFF000;
        if ((PDE_base == 0) or (PDE_base > (self.mem_size - _4K))):
            return None;
        tmp = self.ReadPhysical64(PDE_base + (PDE_index * 8));
        if ((tmp & 0x1) == 0):
            return None;
        if (tmp & 0x80): #This page is a large one (2M) !
            tmpPhysical = ((tmp & 0xfffffffe00000) | (address & 0x00000000001FFFFF));
            if ((tmpPhysical == 0) or (tmpPhysical > (self.mem_size - _2M))):
                return None;
            return (_2M, tmpPhysical)
        PTE_base = tmp & 0x0000FFFFFFFFF000;
        if ((PTE_base == 0) or (PTE_base > (self.mem_size - _4K))):
            return None;
        tmp = self.ReadPhysical64(PTE_base + (PTE_index * 8))
        if ((tmp & 0x1) == 0):
            return None;
        P_base = tmp & 0x0000FFFFFFFFF000;
        if ((P_base == 0) or (P_base > (self.mem_size - _4K))):
            return None;
        return (_4K, (P_base | P_offset))


    def ReadVirtualMemory(self, address, size):
        data = ""
        left_to_read = size
        while left_to_read > 0:
            ret =  self.V2P(address)
            if ret == None:
                return None
            (page_size, physical_address) = ret
            page_base = physical_address & ~(page_size - 1)
            page_end = page_base + page_size
            left_on_page = page_end - physical_address
            byte_to_read = min(left_on_page, left_to_read)
            tmp_data = self.ReadyPhysicalMemory(physical_address, byte_to_read)
            if tmp_data ==  None:
                return None
            data += tmp_data
            left_to_read = left_to_read - byte_to_read
        return data

    def GetStateChanged(self):
        return False

    def GetState(self):
        return self.STATE_PAUSED

    def SingleStep(self):
        return True

    def Resume(self):
        return True

    def UnsetBreakpoint(self, a0):
        return True


#TODO ! Use VMSN parsing !!!!!
"""
#!/usr/bin/python

import struct
import sys
import mmap

def nullstrip(s):
    try:
        return s[:s.index('\x00')]
    except:
        return s

def dump(f):
    for i in range(0, 5):
        for j in range(0, 16):
            Unk3 = struct.unpack("B", f.read(1))[0]
            print "%02x " % Unk3,
        print ""

f = open(VMSN_FILENAME)

Magic = struct.unpack("I", f.read(4))[0]
print "Magic %x" % Magic
Unk = struct.unpack("I", f.read(4))[0]
print "Unk %d" % Unk
GroupCount = struct.unpack("I", f.read(4))[0]
print "GroupCount %d" % GroupCount

for i in range(0, GroupCount):
    Name = nullstrip(f.read(64))
    print "Name %s" % Name
    TagOffset = struct.unpack("Q", f.read(8))[0]
    print "TagOffset %d" % (TagOffset)
    Unk2 = struct.unpack("Q", f.read(8))[0]
    print "Unk2 %d" % Unk2

    if "cpu" == Name:
        f.seek(TagOffset, 0)
        for j in range(0, 4):
            print "---------------TAG-----------------"
            TagFlags = struct.unpack("B", f.read(1))[0]
            print "TagFlags %d" % TagFlags
            TagDataSize = TagFlags & 0x3F
            print "TagDataSize %d" % TagDataSize
            TagNameSize = struct.unpack("B", f.read(1))[0]
            print "TagNameSize %d" % TagNameSize
            TagName = f.read(TagNameSize)
            print "TagName %s" % TagName
            TagData = f.read(TagDataSize)
            #f.read(4)
        break

f.seek(36, 1)


#This is crappy, I know but ok for now !
f.seek(0x8CC0, 0)
Name = nullstrip(f.read(3))
Cpuid = struct.unpack("B", f.read(1))
Null = f.read(3)
if Name != "rip":
    print "Name %s" % list(Name)
    print "Failed !"
    sys.exit(0)
rip = struct.unpack("Q", f.read(8))[0]
print "rip 0x%x" % (rip)

f.seek(28, 1)
Name = nullstrip(f.read(6))
Cpuid = struct.unpack("B", f.read(1))
Null = f.read(5)
if Name != "gpregs":
    print "Failed !"
    sys.exit(0)

#6 rsp
#7 rbp
register_names = [  "rax",
                    "rbx",
                    "rcx",
                    "rdx",
                    "rdi",
                    "rsi",
                    "rbp",
                    "rsp",
                    "r8",
                    "r9",
                    "r10",
                    "r11",
                    "r12",
                    "r13",
                    "r14",
                    "r15",
                    "rip",
                    "rflags",
                    "cs",
                    "fs",
                    "gs",
                ]
for i in range(0, 20):
    print "%s 0x%x" % (register_names[i], struct.unpack("Q", f.read(8))[0])

f.seek(908, 1)



dump(f)
sys.exit(0)
"""

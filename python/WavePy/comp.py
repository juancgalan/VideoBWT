'''
Created on 07/09/2012

@author: zenathar
'''

import numpy as np
from wavelet import *
import itertools as it
import math
from lwt import *
import dwt
import cv
import sys
import pickle

if __name__ == '__main__':
    pass

def spiht_image_pack(img, wavename, level, bpp, mode = "bi.orth", delta = 0.01, display_progress = True, str_pr = "", d = {}, handle = True):
    if not isinstance(img,tuple):
        img = (img)
        bpp = (bpp)
    ch_stream = {
            "size": 0,
            "channels":len(img),
            "bpp":bpp,
            "quant_delta":delta,
            "wave_type": wavename,
            "mode":mode,
            "decomp_level":level,
            "wise_bit":[],
            "payload":[]
            }
    for i in range(len(img)):
        m = np.asarray(img[i])
        if mode == "bi.orth":
            w = wavename(m,level,False)
        else:
            w = dwt.dwt2(m,wavename,level,mode)
        stream = spiht_pack(w,bpp[i],delta,display_progress,str_pr + "[channel "+str(i)+"]",d,handle)
        ch_stream["payload"] += stream["payload"]
        ch_stream["wave_type"] = w.name
        ch_stream["size"] += stream["size"]
        ch_stream["wise_bit"] += [stream["wise_bit"]]
        ch_stream["rows"] = stream["rows"]
        ch_stream["cols"] = stream["cols"]
    return ch_stream

def spiht_image_unpack(frame, display_progress = True, str_pr = "", d = {}, handle = True):
    rgb = []
    for i in range(frame["channels"]):
        pack = {
            "rows":frame["rows"],
            "cols":frame["cols"],
            "channels": 1,
            "wave_type":frame["wave_type"],
            "bpp":frame["bpp"],
            "quant_delta":frame["quant_delta"],
            "decomp_level":frame["decomp_level"],
            "wise_bit":frame["wise_bit"][i],
            "payload":frame["payload"][i]
            }
        wave = spiht_unpack(pack,True,str_pr + "[channel "+str(i)+"]", d, handle)
        if frame["wave_type"] == 'cdf97':
            ch = icdf97(wave,False)
        elif frame["wave_type"] == 'cdf53':
            ch = icdf53(wave,False)
        else:
            ch = dwt.dwt2(wave,frame["wave_type"],frame["decomp_level"],frame["mode"])
        ch = ch - ch.min()
        ch = ch / ch.max() * 255
        ch_i = np.zeros((len(ch),len(ch[0])),np.uint8)
        ch_i[:] = ch
        rgb += [cv.fromarray(ch_i)]
    return tuple(rgb)

def spiht_pack(wave,bpp,delta = 0.01, display_progress=True, str_pr = "", d = {}, handle = True):
    """Compresses a wavelet with SPIHT.

    Runs the original SPIHT algorithm from Dr. Pearlsman paper over the 
    given wavelet.

    Args:
        wavelet: A wavelet to be compressed, must be wavelet2D data type
        bpp: Bits per pixel compression ratio
        delta: Quantization delta if wavelet data is on floating point. 
            This leads to lossy compression always if coefficients are not 
            int
        display_progress: True if you want to print on screen algorithm 
                    progress

    Returns:
        A dictionary with a structure with the compressed data and some 
            decoding info. For example:
        {
            "size":0,
            "wave_type":"db7",
            "bpp":0.5,
            "quant_delta":0.001,
            "payload":[]
        }
    """
    filename = str(len(wave.data)) + "x" + str(len(wave.data[0])) + ".dol"
    if not d:
        try:
            f = open(filename,"r")
            d = pickle.load(f)
            f.close()
            handle = True
        except IOError as e:
            d = {}
            handle = True
    update = len(d)
    codec = SPIHT()
    codec.wavelet = wave
    codec.bpp = bpp
    codec.delta = delta
    codec.check_floating_point()
    codec.str_pr = str_pr
    codec.display_progress = display_progress
    codec.d_memory = d
    codec.compress()
    stream = codec.output_stream.to_list()
    pack = {
            "size":len(stream),
            "rows":len(wave.data),
            "cols":len(wave.data[0]),
            "channels": 1,
            "wave_type":wave.name,
            "bpp":(bpp),
            "quant_delta":delta,
            "decomp_level":wave.level,
            "wise_bit":codec.n,
            "payload":[stream]
            }
    if len(codec.d_memory) > update and handle:
        f = open(filename,"w+")
        pickle.dump(codec.d_memory,f)
        f.close()
    return pack

def spiht_unpack(frame, display_progress=True, str_pr = "",d = {}, handle = True):
    """De-compresses a wavelet with SPIHT.

    Runs the original SPIHT algorithm from Dr. Pearlsman paper over the 
    given wavelet.

    Args:
        frame: A previously compressed frame
        display_progress: True if you want to print on screen algorithm 
                    progress

    Returns:
        An uncompressed wavelet2D instance 
    """
    filename = str(frame["rows"]) + "x" + str(frame["cols"]) + ".dol" 
    if not d:
        try:
            f = open(filename,"r")
            d = pickle.load(f)
            f.close()
            handle = True
        except IOError as e:
            d = {}
            handle = True
    update = len(d)
    codec = SPIHT()
    data = np.zeros((frame["rows"],frame["cols"]),np.int)
    codec.wavelet = wavelet2D(data,frame["decomp_level"],frame["wave_type"])
    codec.delta = frame["quant_delta"]
    codec.str_pr = str_pr
    codec.n = frame["wise_bit"]
    codec.d_memory = d
    codec.output_stream = stream_buffer(frame["payload"],len(frame["payload"]))
    codec.uncompress()
    if len(codec.d_memory) > update and handle:
        f = open(filename,"w+")
        pickle.dump(codec.d_memory,f)
        f.close()
    return codec.wavelet

def fvht_image_pack(img, wavename, level, f_center, Lbpp, lbpp, alpha, c, gamma, mode = "bi.orth", delta = 0.01, display_progress = True, str_pr = "", d = {}, handle = True):
    if not isinstance(img,tuple):
        img = (img)
    ch_stream = {
            "size": 0,
            "channels":len(img),
            "bpp":Lbpp,
            "quant_delta":delta,
            "wave_type": wavename,
            "mode":mode,
            "decomp_level":level,
            "wise_bit":[],
            "Lbpp": Lbpp,
            "lbpp": lbpp,
            "alpha": "alpha",
            "c": c,
            "gamma": gamma,
            "fovea_center": f_center,
            "payload":[]
            }
    for i in range(len(img)):
        m = np.asarray(img[i])
        if mode == "bi.orth":
            w = wavename(m,level,False)
        else:
            w = dwt.dwt2(m,wavename,level,mode)
        stream = fvht_pack(w, f_center, Lbpp, lbpp, alpha, c, gamma, delta, display_progress,str_pr + "[channel "+str(i)+"]",d,handle)
        ch_stream["payload"] += stream["payload"]
        ch_stream["wave_type"] = w.name
        ch_stream["size"] += stream["size"]
        ch_stream["wise_bit"] += [stream["wise_bit"]]
        ch_stream["rows"] = stream["rows"]
        ch_stream["cols"] = stream["cols"]
        ch_stream["bits"] = stream["bits"]
    return ch_stream

def fvht_image_unpack(frame, display_progress = True, str_pr = "", d = {}, handle = True):
    rgb = []
    for i in range(frame["channels"]):
        pack = {
            "rows":frame["rows"],
            "cols":frame["cols"],
            "channels": 1,
            "wave_type":frame["wave_type"],
            "bpp":frame["bpp"],
            "quant_delta":frame["quant_delta"],
            "decomp_level":frame["decomp_level"],
            "wise_bit":frame["wise_bit"][i],
            "payload":frame["payload"][i],
            "Lbpp": frame["Lbpp"],
            "lbpp": frame["lbpp"],
            "alpha": frame["alpha"],
            "c": frame["c"],
            "gamma": frame["gamma"],
            "fovea_center": frame["fovea_center"]
            }
        wave = fvht_unpack(pack,True,str_pr + "[channel "+str(i)+"]", d, handle)
        if frame["wave_type"] == 'cdf97':
            ch = icdf97(wave,False)
        elif frame["wave_type"] == 'cdf53':
            ch = icdf53(wave,False)
        else:
            ch = dwt.dwt2(wave,frame["wave_type"],frame["decomp_level"],frame["mode"])
        ch = ch - ch.min()
        ch = ch / ch.max() * 255
        ch_i = np.zeros((len(ch),len(ch[0])),np.uint8)
        ch_i[:] = ch
        rgb += [cv.fromarray(ch_i)]
    return tuple(rgb)

def fvht_pack(wave, f_center, Lbpp, lbpp, alpha, c, gamma, delta = 0.01, display_progress=True, str_pr = "", d = {}, handle = True):
    """Compresses a wavelet with SPIHT.

    Runs the original SPIHT algorithm from Dr. Pearlsman paper over the 
    given wavelet.

    Args:
        wavelet: A wavelet to be compressed, must be wavelet2D data type
        bpp: Bits per pixel compression ratio
        delta: Quantization delta if wavelet data is on floating point. 
            This leads to lossy compression always if coefficients are not 
            int
        Lbpp: minimum bit rate and final bit rate compression
        lbpp: maximum bit rate compression at the fovea edges
        alpha: fovea area in percent
        c: constant of the power law function
        gamma: pow of the powerlaw function
        display_progress: True if you want to print on screen algorithm 
                    progress

    Returns:
        A dictionary with a structure with the compressed data and some 
            decoding info. For example:
        {
            "size":0,
            "wave_type":"db7",
            "bpp":0.5,
            "quant_delta":0.001,
            "payload":[]
        }
    """
    filename = str(len(wave.data)) + "x" + str(len(wave.data[0])) + ".dol"
    if not d:
        try:
            f = open(filename,"r")
            d = pickle.load(f)
            f.close()
            handle = True
        except IOError as e:
            d = {}
            handle = True
    update = len(d)
    codec = FVHT()
    codec.wavelet = wave
    codec.bpp = Lbpp
    codec.delta = delta
    codec.check_floating_point()
    codec.str_pr = str_pr
    codec.display_progress = display_progress
    codec.d_memory = d
    codec.Lbpp = Lbpp
    codec.lbpp = lbpp
    codec.alpha = alpha
    codec.c = c
    codec.gamma = gamma
    codec.P = f_center
    codec.compress()
    stream = codec.output_stream.to_list()
    pack = {
            "size":len(stream),
            "rows":len(wave.data),
            "cols":len(wave.data[0]),
            "channels": 1,
            "wave_type":wave.name,
            "quant_delta":delta,
            "decomp_level":wave.level,
            "wise_bit":codec.n,
            "Lbpp": Lbpp,
            "lbpp": lbpp,
            "alpha": alpha,
            "c": c,
            "gamma": gamma,
            "fovea_center" : f_center,
            "bits": codec.amount_of_bits,
            "payload":[stream]
            }
    if len(codec.d_memory) > update and handle:
        f = open(filename,"w+")
        pickle.dump(codec.d_memory,f)
        f.close()
    return pack

def fvht_unpack(frame, display_progress=True, str_pr = "",d = {}, handle = True):
    """De-compresses a wavelet with SPIHT.

    Runs the original SPIHT algorithm from Dr. Pearlsman paper over the 
    given wavelet.

    Args:
        frame: A previously compressed frame
        display_progress: True if you want to print on screen algorithm 
                    progress

    Returns:
        An uncompressed wavelet2D instance 
    """
    filename = str(frame["rows"]) + "x" + str(frame["cols"]) + ".dol" 
    if not d:
        try:
            f = open(filename,"r")
            d = pickle.load(f)
            f.close()
            handle = True
        except IOError as e:
            d = {}
            handle = True
    update = len(d)
    codec = FVHT()
    data = np.zeros((frame["rows"],frame["cols"]),np.uint)
    codec.wavelet = wavelet2D(data,frame["decomp_level"],frame["wave_type"])
    codec.bpp = frame["Lbpp"]
    codec.delta = frame["quant_delta"]
    codec.str_pr = str_pr
    codec.n = frame["wise_bit"]
    codec.d_memory = d
    codec.output_stream = stream_buffer(frame["payload"][0],len(frame["payload"][0]))
    codec.Lbpp = frame["Lbpp"]
    codec.lbpp = frame["lbpp"]
    codec.alpha = frame["alpha"]
    codec.c = frame["c"]
    codec.gamma = frame["gamma"]
    codec.P = frame["fovea_center"]
    codec.uncompress()
    if len(codec.d_memory) > update and handle:
        f = open(filename,"w+")
        pickle.dump(codec.d_memory,f)
        f.close()
    return codec.wavelet


class SPIHT(object):
    '''
    This class represents a SPIHT codec. It can compress and decompress
    data from Wavelet2D data type.

    This class is based on the original paper of Dr. Pearlsman
    '''

    #bpp resolution for compression
    bpp = 0
    #inner wavelet data type structure
    wavelet = 0
    #Quantization delta for floating point wavelets
    delta = 0.01
    #Estra info for progress display
    str_pr = ""
    display_progress = True
    d_memory = {}

    def __init__(self):
        pass

    def check_floating_point(self):
        ints = [np.int, np.int16, np.int32, np.int64]
        if not self.wavelet.data.dtype in ints:
            self.wavelet = quant(self.wavelet,self.delta)

    def init(self):
        self.LSP = []
        rows = len(self.wavelet.data) / 2 ** (self.wavelet.level-1 )
        cols = len(self.wavelet.data[0]) / 2 ** (self.wavelet.level-1)
        self.LIP = get_z_order(rows*cols)
        self.LIS = get_z_order(rows*cols)[rows*cols/4:]
        for i in self.LIS:
            i.entry_type = "A"
        return

    def S_n(self, Tau, n):
        T = np.array([i.tolist() for i in Tau])
        return (abs(self.wavelet.data[T[:,0],T[:,1]]).max() >> int(n)) & 1

    def bitplane_encoding(self, power, output):
        for p in self.LSP:
            output.append((self.wavelet.data[p[0]][p[1]] & 2 ** power) >> power)

    def inv_bitplane_encoding(self, power):
        for p in self.LSP:
            bt = self.output_stream.pop()
            self.wavelet.data[p[0],p[1]] = self.wavelet.data[p[0],p[1]] | bt << power
            if self.output_stream.pointer == self.output_stream.size:
                break

    #Get descendants, Pearlman named this set D
    """   
    def get_D(self, ij):
        if self.d_memory.has_key(ij):
            return self.d_memory[ij]
        O = self.get_O(ij)
        D = np.zeros(2**((self.wavelet.level-1)*2))
        D += O
        window_size = 4
        while O:
        #while np.all((4 * root) < max_root):
            reverse_D = D[::-1]
            for i in range(window_size):
                O = self.get_O(reverse_D[i])
                D += O
            window_size *= 4 #Window size increases as rows x 2 and cols x 2
        return D"""

    def get_D(self, ij):
        try:
            return self.d_memory[ij.__hash__()]
        except KeyError:
            Di = []
            O = self.get_O(ij)
            Di += O
            window_size = 4
            while O:
                reverse_D = Di[::-1]
                for i in range(window_size):
                    O = self.get_O(reverse_D[i])
                    Di += O
                window_size *= 4 #Window size increases as rows x 2 and cols x 2
            self.d_memory[ij.__hash__()] = Di
            return Di
    #Get offsprings of ij, Pearlman named this set O
    def get_O(self, ij):
        if self.has_offspring(ij):
            return [2*ij, 2*ij+(1,0), 2*ij+(0,1), 2*ij+(1,1)]
        else:
            return []

    #Get all subsets of ij decendants O,D and L
    def get_DOL(self, ij):
        D = self.get_D(ij)
        O = D[:4]
        L = D[4:]
        return D, O, L

    def has_offspring(self, ij, typ = bool):
        if ij*2 < (len(self.wavelet.data),len(self.wavelet.data[0])):
            if typ == bool:
                return True
            else:
                return 1
        else:
            if typ == bool:
                return False
            else:
                return 1
    #outputs coefficient sign
    def out_sign(self, coeff):
        if self.wavelet.data[coeff[0],coeff[1]] > 0:
            return 0
        else:
            return 1

    def sorting(self, n):
        nextLSP = []                                                    
        removeLIP = []
        #Check for each significant pixel on the LIP
        c = -1
        for ij in self.LIP:
            c += 1
            out = self.S_n([ij], n)
            self.output_stream += [out]
            if out == 1:
                nextLSP += [ij]
                self.output_stream += [self.out_sign(ij)]
                removeLIP += [ij]
        #Remove new Significant pixels from LIP list
        #This is done after the output so the for loop doesnt have any problem
        for i in removeLIP:
            self.LIP.remove(i)
        remove_from_LIS = []
        for ij in self.LIS:
        #Check for zerotree roots (2.2.1)
            D, O, L = self.get_DOL(ij)
            if ij.entry_type == 'A':
                out = self.S_n(D,n)
                self.output_stream += [out]
                if out == 1:
                    for kl in O:
                        out = self.S_n([kl],n)
                        self.output_stream += [out]
                        if out == 1:
                            nextLSP += [kl]
                            self.output_stream += [self.out_sign(kl)]
                        else:
                            self.LIP += [kl]
                #Check if ij has grandsons, if not remove from LIS
                    if L:
                        ij.entry_type = "B"
                        self.LIS += [ij]
                    else:
                        pass
                    remove_from_LIS += [ij]
            else: #Entry is type B
                out = self.S_n(L,n)
                self.output_stream += [out]
                if out == 1:
                    for k in O:
                        k.entry_type = "A"
                    self.LIS += O
                    remove_from_LIS += [ij]
        for i in remove_from_LIS:
            self.LIS.remove(i)
        remove_from_LIS = [] 
        return nextLSP 

    def compress(self):
        maxs = abs(self.wavelet.data)
        self.n = int(math.log(maxs.max(),2))
        n = self.n
        self.init()
        bit_bucket = self.bpp * len(self.wavelet.data) * len(self.wavelet.data[0])
        self.output_stream=stream_buffer([],bit_bucket,self.display_progress,self.str_pr)
        #self.output_stream = []
        while n >= 0:
            try:
                newLSP = self.sorting(n)
                self.bitplane_encoding(n,self.output_stream)
                self.LSP += newLSP
                n -= 1
            except NameError as e:
                print e
                return

    def inv_sorting(self,n):
        nextLSP = []
        #Fill each significant pixel
        removeLIP = []
        for ij in self.LIP:
            out = self.output_stream.pop()
            if out == 1:
                nextLSP += [ij]
                self.wavelet.data[ij[0],ij[1]] |= (1 << n)
                sign = self.output_stream.pop()
                if sign:
                    self.wavelet.data[ij[0],ij[1]] *= -1
                removeLIP += [ij]
        for i in removeLIP:
            self.LIP.remove(i)
        remove_from_LIS = []
        for ij in self.LIS:
            D, O, L = self.get_DOL(ij)
            if ij.entry_type == "A":
                out = self.output_stream.pop()
                if out == 1:
                    for kl in O:
                        out = self.output_stream.pop()
                        if out == 1:
                            nextLSP += [kl]
                            sign = self.output_stream.pop()
                            self.wavelet.data[kl[0],kl[1]] |= (1 << n)
                            if sign:
                                self.wavelet.data[kl[0],kl[1]] *= -1
                        else:
                            self.LIP += [kl]
                    if L:
                        ij.entry_type = "B"
                        self.LIS += [ij]
                    else:
                        pass
                    remove_from_LIS += [ij]
            else:
                out = self.output_stream.pop() 
                if out == 1:
                    for i in O:
                        i.entry_type = "A"
                    self.LIS += O
                    remove_from_LIS += [ij]
        remove_from_LIS.reverse()
        for i in remove_from_LIS:
            self.LIS.remove(i)
        remove_from_LIS = []
        return nextLSP

    def uncompress(self):
        self.init()
        self.output_stream.reverse()
        n = self.n
        while n >= 0:
            try:
                newLSP = self.inv_sorting(n)
                self.inv_bitplane_encoding(n)
                self.LSP += newLSP
                n -= 1
            except IndexError:
                break
                    
class FVHT(object):
    '''
    This class represents a SPIHT codec. It can compress and decompress
    data from Wavelet2D data type.

    This class is based on the original paper of Dr. Pearlsman
    '''

    #Highest bpp resolution for compression
    Lbpp = 0
    #Lowest bpp resolution for compression
    lbpp = 0 
    #Area of the fovea to be compressed at highest bpp
    fovea_tap = 0
    #Distance of the observer
    dist = 0
    #inner wavelet data type structure
    wavelet = 0
    #Quantization delta for floating point wavelets
    delta = 0.01
    #Extra info for progress display
    str_pr = ""
    display_progress = True
    #DOL sets memory cache
    d_memory = {}
    #Fovea center
    P = (0,0)
    #fovea area
    alpha = 0
    #calculated fovea length
    fovea_length = 0
    
    #power law parameters
    c = 1
    gamma = 1

    #TESTING Variables
    amount_of_bits = 0

    def __init__(self):
        pass

    def check_floating_point(self):
        ints = [np.int, np.int16, np.int32, np.int64]
        if not self.wavelet.data.dtype in ints:
            self.wavelet = quant(self.wavelet,self.delta)

    def init(self):
        self.LSP = []
        rows = len(self.wavelet.data) / 2 ** (self.wavelet.level-1 )
        cols = len(self.wavelet.data[0]) / 2 ** (self.wavelet.level-1)
        self.LIP = get_z_order(rows*cols)
        self.LIS = get_z_order(rows*cols)[rows*cols/4:]
        for i in self.LIS:
            i.entry_type = "A"
        return

    def S_n(self, Tau, n):
        T = np.array([i.tolist() for i in Tau])
        return (abs(self.wavelet.data[T[:,0],T[:,1]]).max() >> int(n)) & 1

    def bitplane_encoding(self, power, output):
        removeLSP = []
        for p in self.LSP:
            if self.calculate_fovea_w(p) < self.get_current_bpp():
                pass
            else:
                output.append((self.wavelet.data[p[0]][p[1]] & 2 ** power) >> power)
                self.amount_of_bits[tuple(p)] += 1

    def inv_bitplane_encoding(self, power):
        removeLSP = []
        for p in self.LSP:
            if self.calculate_fovea_w(p) < self.get_current_bpp():
                removeLSP += [ij]
            else:
                bt = self.output_stream.pop()
                self.wavelet.data[p[0],p[1]] = self.wavelet.data[p[0],p[1]] | bt << power
            if self.output_stream.pointer == self.output_stream.size:
                break
        #for i in removeLSP:
        #    self.LSP.remove(i)

    #Get descendants, Pearlman named this set D
    def get_D(self, ij):
        try:
            return self.d_memory[ij.__hash__()]
        except KeyError:
            Di = []
            O = self.get_O(ij)
            Di += O
            window_size = 4
            while O:
                reverse_D = Di[::-1]
                for i in range(window_size):
                    O = self.get_O(reverse_D[i])
                    Di += O
                window_size *= 4 #Window size increases as rows x 2 and cols x 2
            self.d_memory[ij.__hash__()] = Di
            return Di
    #Get offsprings of ij, Pearlman named this set O
    def get_O(self, ij):
        if self.has_offspring(ij):
            return [2*ij, 2*ij+(1,0), 2*ij+(0,1), 2*ij+(1,1)]
        else:
            return []
    #Get all subsets of ij decendants O,D and L
    def get_DOL(self, ij):
        D = self.get_D(ij)
        O = D[:4]
        L = D[4:]
        return D, O, L

    def has_offspring(self, ij, typ = bool):
        if ij*2 < (len(self.wavelet.data),len(self.wavelet.data[0])):
            if typ == bool:
                return True
            else:
                return 1
        else:
            if typ == bool:
                return False
            else:
                return 1
    #outputs coefficient sign
    def out_sign(self, coeff):
        if self.wavelet.data[coeff[0],coeff[1]] > 0:
            return 0
        else:
            return 1

    def sorting(self, n):
        nextLSP = []                                                    
        removeLIP = []
        #Check for each significant pixel on the LIP
        for ij in self.LIP:
            out = self.S_n([ij], n)
            self.output_stream += [out]
            if out == 1:
                if self.calculate_fovea_w(ij) <= self.get_current_bpp():
                    removeLIP += [ij]
                else:
                    nextLSP += [ij]
                    self.amount_of_bits[tuple(ij)] = 1
                    self.output_stream += [self.out_sign(ij)]
                    removeLIP += [ij]
        #Remove new Significant pixels from LIP list
        #This is done after the output so the for loop doesnt have any problem
        for i in removeLIP:
            self.LIP.remove(i)
        remove_from_LIS = []
        for ij in self.LIS:
        #Check for zerotree roots (2.2.1)
            D, O, L = self.get_DOL(ij)
            if ij.entry_type == 'A':
                out = self.S_n(D,n)
                self.output_stream += [out]
                if out == 1:
                    for kl in O:
                        out = self.S_n([kl],n)
                        self.output_stream += [out]
                        if out == 1:
                            if self.calculate_fovea_w(kl) >= self.get_current_bpp():
                                nextLSP += [kl]
                                self.output_stream += [self.out_sign(kl)]
                                self.amount_of_bits[tuple(ij)] = 1
                        else:
                            self.LIP += [kl]
                #Check if ij has grandsons, if not remove from LIS
                    if L:
                        ij.entry_type = "B"
                        self.LIS += [ij]
                    else:
                        pass
                    remove_from_LIS += [ij]
            else: #Entry is type B
                out = self.S_n(L,n)
                self.output_stream += [out]
                if out == 1:
                    for k in O:
                        k.entry_type = "A"
                    self.LIS += O
                    remove_from_LIS += [ij]
        for i in remove_from_LIS:
            self.LIS.remove(i)
        remove_from_LIS = [] 
        return nextLSP 

    def compress(self):
        maxs = abs(self.wavelet.data)
        self.n = int(math.log(maxs.max(),2))
        n = self.n
        self.init()
        bit_bucket = self.bpp * self.wavelet.cols * self.wavelet.rows
        self.output_stream=stream_buffer([],bit_bucket,self.display_progress,self.str_pr)
        self.calculate_fovea_length()
        self.amount_of_bits = np.zeros((len(self.wavelet.data), len(self.wavelet.data[0])))
        #self.output_stream = []
        while n >= 0:
            try:
                newLSP = self.sorting(n)
                self.bitplane_encoding(n,self.output_stream)
                self.LSP += newLSP
                n -= 1
            except BufferFullException as e:
                return

    def inv_sorting(self,n):
        nextLSP = []
        #Fill each significant pixel
        removeLIP = []
        for ij in self.LIP:
            out = self.output_stream.pop()
            if out == 1:
                if self.calculate_fovea_w(ij) <= self.get_current_bpp():
                    removeLIP += [ij]
                    continue
                else:
                    nextLSP += [ij]
                    self.wavelet.data[ij[0],ij[1]] |= (1 << n)
                    sign = self.output_stream.pop()
                    if sign:
                        self.wavelet.data[ij[0],ij[1]] *= -1
                    removeLIP += [ij]
        for i in removeLIP:
            self.LIP.remove(i)
        remove_from_LIS = []
        for ij in self.LIS:
            D, O, L = self.get_DOL(ij)
            if ij.entry_type == "A":
                out = self.output_stream.pop()
                if out == 1:
                    for kl in O:
                        out = self.output_stream.pop()
                        if out == 1:
                            if self.calculate_fovea_w(kl) >= self.get_current_bpp():
                                nextLSP += [kl]
                                sign = self.output_stream.pop()
                                self.wavelet.data[kl[0],kl[1]] |= (1 << n)
                                if sign:
                                    self.wavelet.data[kl[0],kl[1]] *= -1
                        else:
                            self.LIP += [kl]
                    if L:
                        ij.entry_type = "B"
                        self.LIS += [ij]
                    else:
                        pass
                    remove_from_LIS += [ij]
            else:
                out = self.output_stream.pop() 
                if out == 1:
                    for i in O:
                        i.entry_type = "A"
                    self.LIS += O
                    remove_from_LIS += [ij]
        remove_from_LIS.reverse()
        for i in remove_from_LIS:
            self.LIS.remove(i)
        remove_from_LIS = []
        return nextLSP

    def uncompress(self):
        self.init()
        self.output_stream.reverse()
        n = self.n
        self.calculate_fovea_length()
        while n >= 0:
            try:
                newLSP = self.inv_sorting(n)
                self.inv_bitplane_encoding(n)
                self.LSP += newLSP
                n -= 1
            except IndexError:
                break
 
    def get_current_bpp(self):
        bpp = float(self.output_stream.pointer)
        bpp /= self.output_stream.size
        return bpp
    
    def calculate_fovea_w(self, ij):
        try:
            P = self.get_center(ij)
        except NameError:
            return self.Lbpp
        H = len(self.wavelet.data)
        W = len(self.wavelet.data[0])
        d = self.norm(P[1] - ij[1],P[0] - ij[0]) * 2**P[2] / self.fovea_length
        if d<self.alpha:
            return self.Lbpp
        elif d>=1:
            return self.lbpp
        else:
            return self.powerlaw(d) * (self.Lbpp - self.lbpp) + self.lbpp
    
    def norm(self,x,y):
        return math.sqrt(float(x**2 + y ** 2))
    
    def powerlaw(self,n):
        return self.c * (1 - ((n-self.alpha) / (1-self.alpha))) ** self.gamma
        
    def get_center(self,ij):
        if (ij[0] == 0 and ij[1] == 0):
            raise NameError("ij on HH")
        else:
            if ij[0] == 0:
                aprx_level_r = self.wavelet.level + 1
            else:
                aprx_level_r = math.ceil(math.log(self.wavelet.rows/float(ij[0]),2))
                if aprx_level_r > self.wavelet.level:
                    aprx_level_r = self.wavelet.level + 1
            if ij[1] == 0:
                aprx_level_c = self.wavelet.level + 1
            else:
                aprx_level_c = math.ceil(math.log(self.wavelet.rows/float(ij[1]),2))
                if aprx_level_c > self.wavelet.level:
                    aprx_level_c = self.wavelet.level + 1
            if (aprx_level_r > self.wavelet.level) and (aprx_level_c > self.wavelet.level):
                raise NameError("ij on HH")
            if aprx_level_r <= aprx_level_c:
                aprx_level = aprx_level_r
            else:
                aprx_level = aprx_level_c
            y = float(self.P[0]) / 2**aprx_level
            x = float(self.P[1]) / 2**aprx_level 
            if aprx_level_r == aprx_level:
                y += float(self.wavelet.rows) / 2**aprx_level
            if aprx_level_c == aprx_level:
                x += float(self.wavelet.cols) / 2**aprx_level
            return (y, x, aprx_level)
    
    def calculate_fovea_length(self):
        H = len(self.wavelet.data)
        W = len(self.wavelet.data[0])
        k = np.zeros(4)
        k[0] = self.norm(self.P[0],H-self.P[1])
        k[1] = self.norm(W-self.P[0],self.P[1])
        k[2] = self.norm(W-self.P[0],H-self.P[1])
        k[3] = self.norm(self.P[0],H-self.P[1])
        self.fovea_length = k.max()
        
    def printFoveaWindow(self):
        window = np.zeros((self.wavelet.rows, self.wavelet.cols))
        points = get_z_order(self.wavelet.rows * self.wavelet.cols)
        for i in points:
            window[tuple(i)] = self.calculate_fovea_w(i)
        return window
                
class stream_buffer(object):
    size = 1024
    str_ptr = ""
    rev = 1
    
    def __init__(self, arg = [], size = 1024, show_progress = True, str_pr = ""):
        self.size = int(size)
        self.str_pr = str_pr
        if not arg:
            self.data = np.zeros(size, np.int)
            self.pointer = 0
        else:
            self.data = np.array(arg)
            self.pointer = len(arg)-1
        self.show_progress = show_progress

    def __iadd__(self, other):
        if self.pointer < self.size:
            if self.show_progress:
                print ('progress: {0:.4f}'+self.str_pr).format(float(self.pointer) / self.size * 100)
            self.data[self.pointer] = other[0]
            self.pointer += self.rev*1
            return self 
        else:
            raise BufferFullException("Stream full")

    def append(self,other):
        if self.pointer < self.size:
            self += [other]
            return self
        else:
            raise BufferFullException("Stream full")

    def to_list(self):
        return list(self.data)

    def pop(self):
        if self.show_progress:
            print ('progress: {0:.4f}' + self.str_pr).format(float(self.pointer)/self.size * 100)
            self.pointer -= self.rev*1
        return self.data[self.pointer - 1]
   
    def reverse(self):
        self.rev = self.rev*-1
        self.pointer = 0

class buffer(list):
    size = 1024
    str_pr = ""

    def __init__(self, arg = [], size = 1024, show_progress = True, str_pr = ""):
        super(buffer, self).__init__(arg)
        self.size = size
        self.str_pr = str_pr
        self.show_progress = show_progress

    def __iadd__(self, other):
        if len(self) <= self.size:
            if self.show_progress:
                print ('progress: {0:.2f}'+self.str_pr).format(float(len(self)) / self.size * 100)
            return buffer(self + other,self.size)
        else:
            raise NameError("Stream full")

    def append(self,other):
        if len(self) <= self.size:
            super(buffer,self).append(other)
        else:
            raise NameError("Stream full")

    def to_list(self):
        return list(self)

    def pop(self):
        if self.show_progress:
            print ('progress: {0:.2f}' + self.str_pr).format(float(len(self))/self.size * 100)
        return super(buffer,self).pop()

def quant(wavelet,delta):
    iw = np.zeros((len(wavelet.data),len(wavelet.data[0])),np.int)
    iw= np.array(np.trunc(wavelet.data / delta), np.int)
    wavelet.data = iw
    return wavelet

class BufferFullException(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)

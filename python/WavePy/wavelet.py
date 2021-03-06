'''
Created on 02/06/2012

@author: zenathar
'''
import numpy as np
from numpy import array 
import math
import cv2
import threading
from collections import deque

def get_z_order(dim):
    mtx = []
    n = int(math.log(dim,2))
    pows = range(int(n/2))
    for i in range(dim):
        x = 0
        y = 0
        for j in pows:
            x |= ((i >> 2*j) & 1) << j 
            y |= ((i >> 2*j+1) & 1) << j 
        mtx += [vector((y,x))]
    return mtx

def get_morton_order(dim, idx = 0, size = -1):
    if size < 0:
        mtx = deque()
    else:
        mtx = deque([],size)
    if idx <> 0:
        swp = idx
        idx = dim
        dim = swp
    n = int(math.log(dim,2))
    pows = range(int(n/2))
    for i in range(dim):
        x = 0
        y = 0
        for j in pows:
            x |= ((i >> 2*j) & 1) << j 
            y |= ((i >> 2*j+1) & 1) << j
        if idx == 0: 
            mtx += [vector((y,x))]
        else:
            idx -= 1
    return mtx

def fromarray(mtx, level, name = ""):
    '''Creates a wavelet2D using a numpy array.

    This method packs a data wavelet coefficients stored on a numpy ndarray
    matrix into a wavelet2D object.

    Args:
        mtx: Coefficient matrix to be packed.
        level: Level of decomposition of the wavelet
        name: Wavelet used to get this coefficients (optional)

    Returns:
        A wavelet2D object packing the information given.
    '''
    return wavelet2D(mtx,level,name)

class wavelet(object):
    def __init__(self):
        print("echo")

class wavelet2D(object):
    '''
    classdocs
    '''
    
    level = 1
    w_type = float
    name = ""
    rows = 0
    cols = 0

    def __init__(self, data, level, name = ""):
        '''
        Constructor
        '''
        if not isinstance(data, np.ndarray) or data.ndim != 2:
            raise TypeError, "data must be a 2D numpy array matrix"
        self.level = level
        self.data = data
        self.name = name
        self.rows = len(data)
        self.cols = len(data[0])
        
    def getHH(self):
        '''
        Returns the HH band of the wavelet
        '''
        data1 = self.data[0:len(self.data) / 2**self.level,0:len(self.data[0]) / 2 ** self.level]
        return data1

    def getLH(self,subdata):
        '''
        Returns the subband LH of a wavelet assuming one level of decomposition
        '''
        data1 = subdata[len(subdata) / 2:,:len(subdata[0]) / 2]
        return data1

    def getHL(self,subdata):
        '''
        Returns the subband HL of a wavelet assuming one level of decomposition
        '''
        data1 = subdata[:len(subdata) / 2,len(subdata[0]) / 2:]
        return data1

    def getLL(self,subdata):
        '''
        Returns the subband LH of a wavelet assuming one level of decomposition
        '''
        data1 = subdata[int(len(subdata) / 2):,int(len(subdata[0]) / 2):]
        return data1

    def getLH_n(self, level):
        '''
        Returns the LH subband of level "level" of the wavelet decomposition
        '''
        level = level - 1
        #calculate the number of rows and columns that the decomposition must have at level - 1
        rows = len(self.data) / 2 ** level
        cols = len(self.data[0]) / 2 ** level
        _subband = self.getLH(self.data[:rows, :cols])
        return _subband
    
    def getHL_n(self, level):
        '''
        Returns the HL subband of level "level" of the wavelet decomposition
        '''
        level = level - 1
        #calculate the number of rows and columns that the decomposition must have at level - 1
        rows = len(self.data) / 2 ** level
        cols = len(self.data[0]) / 2 ** level
        _subband = self.getHL(self.data[:rows, :cols])
        return _subband

    def getLL_n(self, level):
        '''
        Returns the LL subband of level "level" of the wavelet decomposition
        '''
        level = level - 1
        #calculate the number of rows and columns that the decomposition must have at level - 1
        rows = len(self.data) / 2 ** level
        cols = len(self.data[0]) / 2 ** level
        _subband = self.getLL(self.data[:rows, :cols])
        return _subband

    def show(self, name):
        temp = self.data
        #temporal wavelet copy
        w = self.data.copy()
        w = np.abs(w)
        rows = len(w)
        cols = len(w[0])
        #scaling coefficients for display
        m = w.min()
        M = w.max() - m
        w = (w - m) / float(M) * 255
        #Now all bands
        for i in reversed(range(1,self.level+1)):
            #HL
            hl = w[rows/2**i:rows/2**(i-1),:cols/2**i]
            m = hl.min()
            M = hl.max() - m
            if not M==0:
                hl[:] = (hl - m) / float(M) * 255
            #LH
            lh = w[:rows/2**i,cols/2**i:cols/2**(i-1)]
            m = lh.min()
            M = lh.max() - m
            if not M==0:
                lh[:] = (lh - m) / float(M) * 255
            #HL
            hh = w[rows/2**i:rows/2**(i-1),cols/2**i:cols/2**(i-1)]
            m = hh.min()
            M = hh.max() - m
            if not M == 0:
                hh[:] = (hh - m) / float(M) * 255
        #change type to uint8
        w_ui8 = w.view(np.uint8)
        w_ui8_d = w_ui8[:,::w.dtype.itemsize] 
        w_ui8_d[:] = w
        w = w_ui8_d
        self.data = temp
        #show with a thread
        #wm = WindowManager(1)
#        wm.img = cv.fromarray(w.copy())
#        wm.name = name
#        wm.start()
        #cv.ShowImage(name,cv.fromarray(w.copy()))
        #cv.WaitKey(0)
        #cv.DestroyWindow(name)
        return w

class WindowManager(threading.Thread):

    img = 0
    name = "Empty"

    def __init__(self, num):
        threading.Thread.__init__(self)
        self.num = num

    def run(self):
        cv2.imshow(self.name,self.img)
        while True:
            key = cv2.waitKey([0])
            cv2.destroyWindow(self.name)
            print self.name + " destroyed..."
            break

class vector(object):
    def __init__(self, data, entry_type = "-"):
        if isinstance(data,np.ndarray):
            self.data = data
        else:
            self.data = np.array(data)
        self.entry_type = type
        self.deleted = False

    def __hash__(self):
        return hash(tuple(self.data))

    def __add__(self, other):
        if isinstance(other,np.ndarray):
            return vector(self.data + other.data)
        else:
            return vector(self.data + np.array(other))
    def __eq__(self, other):
        if (self.__hash__() == other.__hash__()):
            return True
        else:
            return False

    def __str__(self):
        return self.data.__str__()

    def __repr__(self):
        return self.data.__repr__()

    def __mul__(self,other):
        return vector(self.data * other)

    def __rmul__(self,other):
        return vector(self.data * other)

    def __lt__(self, other):
        if (isinstance(other,np.ndarray)):
            return np.all(self.data < other)
        else:
            return np.all(self.data < np.array(other))

    def tolist(self):
        return self.data.tolist()

    def __getitem__(self,index):
        return self.data[index]

def LoadImageRGB(filename):
    mtx = cv2.imread(filename)
    return splitRGB(mtx)

def splitRGB(image):
    k = np.asarray(image)
    r = k[:,:,0].copy()
    g = k[:,:,1].copy()
    b = k[:,:,2].copy()
    return (r,g,b)

def fuseRGB(ch):
    mtx = np.zeros((len(ch[0]),len(ch[0][0]),3))
    mtx[:,:,0] = ch[0].copy()
    mtx[:,:,1] = ch[1].copy()
    mtx[:,:,2] = ch[2].copy()
    return mtx

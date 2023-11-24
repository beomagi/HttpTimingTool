import time
from collections import deque

iterations=10000

def setupra():
    ra=list(range(1, 100000))
    return ra

def test_rot_type1(ra):
    rafinal=ra[-1]+iterations
    while ra[-1]<rafinal:
        ra=ra[1:]
        ra.append(ra[-1]+1)

def test_rot_type2(ra):
    rafinal=ra[-1]+iterations
    while ra[-1]<rafinal:
        ra.pop(0)
        ra.append(ra[-1]+1)

def test_rot_type3(ra):
    rafinal=ra[-1]+iterations
    while ra[-1]<rafinal:
        q=deque(ra)
        q.popleft()
        ra=list(q)
        ra.append(ra[-1]+1)



if __name__=="__main__":
    ra=setupra()
    tstart=time.time()
    test_rot_type1(ra)
    tend=time.time()
    print("type [1:] -- {}s".format(tend-tstart))
    
    tstart=time.time()
    test_rot_type2(ra)
    tend=time.time()
    print("type .pop(0) -- {}s".format(tend-tstart))
    
    tstart=time.time()
    test_rot_type3(ra)
    tend=time.time()
    print("type deque -- {}s".format(tend-tstart))
    
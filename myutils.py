def cleanget(dictionary, key):
    val = dict()
    if key in dictionary:
        val = dictionary.get(key)
    return val


def invert(dictionary):
    inv = dict()
    for k,v in dictionary.iteritems():
        inv[v] = inv.get(v, [])
        inv[v].append(k)
    return inv

        
def applyAnd(arr):
    "Bitwise AND of arr vector"
    res = None
    if len(arr) > 0:
        res = reduce(lambda x,y: "(" + x + ")&(" + y + ")", arr)
    return res

def applyInv(stateStr, arr):
    "returns an array of mapped invert operations"
    inv = map(applyInvChar, stateStr)
    return map(lambda x,y: x + "(" + y + ")", inv, arr)

def applyOr(arr):
    "Bitwise OR of arr vector"
    res = None
    if len(arr) > 0:
        res = reduce(lambda x,y: "(" + x + ")|(" + y + ")", arr)
    return res

def applyInvChar(state):
    inv = ""
    if state == "0":
        inv = "!"
    return inv

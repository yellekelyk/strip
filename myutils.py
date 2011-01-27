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




foldDict = {
    "5" : ["S"],
    "1" : ["L", "I"],
    "0" : ["O"],
    "8" : ["B"],
    "D" : ["O"],
    "0" : ["O","D"],
    "L" : ["I"],
    "I" : ["L"],
}

foldStrDict = {
    "VV" : ["W"],
    "CL" : ["D"],
    "CI" : ["D"],
    "RN" : ["M"],
    "WW" : ["W"]
}


MAX_M = 100
MAX_N = 100


def getLevenshteinDistance(s: str,t: str,MAX_LEVENSHTEIN_DISTANCE: int = 2) -> int:
    if s == t:
        return 0
    n = len(s)
    m = len(t)
    NO_MATCH_SCORE = n + m
    if  n == 0 or m == 0 or abs(n-m) > MAX_LEVENSHTEIN_DISTANCE:
        return NO_MATCH_SCORE

    d = [[0]*(m+1) for j in range(n+1)]
    for i in range(0, n + 1):
        d[i][0] = i
    for j in range(0, m + 1):
        d[0][j] = j
    transpo = False
    for i in range(1,n+1):

        si = s[i-1]
        skip = False
        for j in range(1,m+1):
            if skip:
                skip = False
                continue
            tj = t[j-1]
            isMatch = fold(si,tj)
            if not isMatch:
                testChars = s[i-1:i+1]
                if foldStr(testChars,tj):
                    isMatch = True
                    skip = True
            cost = 0 if isMatch else 1
            d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1] + cost)

            if i > 1 and j > 1 and (i < n and s[i] == t[j-1]) and (j < m and s[i-1] == t[j])  and s[i] != s[i-1]:
                d[i][j] = min(d[i][j], d[i-2][j-2] + 1)

            min1 = min(i,j)
            if min1<m and min1<n:
                if d[min1][min1] > MAX_LEVENSHTEIN_DISTANCE:
                     return d[min1][min1]
    return d[n][m]

def foldStr(a: str,b: str) -> bool:
    if a in foldStrDict and b in foldStrDict[a]:
        return True
    return False

def fold(a: str,b: str) -> bool:
    if a.upper() == b.upper() :
        return True
    if a in foldDict and b in foldDict[a]:
        return True
    return False

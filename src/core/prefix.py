def makeregprefix(key):
    regstr = [".","+","*","?","|","^","$",]
    for regkey in regstr:
        if key == regkey:
            return r"\{}".format(key)
    return key
VARIABLE_PREFIX = "$"
COMMENT_PREFIX = "#"

VARIABLE_REGPREFIX = makeregprefix(VARIABLE_PREFIX)
COMMENT_REGPREFIX = makeregprefix(COMMENT_PREFIX)

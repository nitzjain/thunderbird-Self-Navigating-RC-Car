#!/usr/bin/python

import sys, getopt
import re

"""
This parses the Vector DBC file to generate code to marshal and unmarshal DBC defined messages

Use Python (3.5 was tested to work)
python dbc_parse.py -i 243.dbc -s MOTOR > generated_code.c
"""

class Signal(object):
    def __init__(self, name, bit_start, bit_size, is_unsigned, scale, offset, min_val, max_val, recipients):
        self.name = name
        self.bit_start = int(bit_start)
        self.bit_size = int(bit_size)
        self.is_unsigned = is_unsigned

        self.offset = float(offset)
        self.offset_str = offset
        self.scale = float(scale)
        self.scale_str = scale
        self.min_val = float(min_val)
        self.min_val_str = min_val
        self.max_val = float(max_val)
        self.max_val_str = max_val

        self.recipients = recipients

    def get_code_var_type(self):
        if '.' in self.scale_str:
            return "float"
        else:
            _max = (2 ** self.bit_size) * self.scale
            if not self.is_unsigned:
                _max *= 2
                
            t = "uint32_t"
            if _max <= 256:
                t = "uint8_t"
            elif _max <= 65536:
                t = "uint16_t"

            if not self.is_unsigned:
                t = t[1:]

            return t


class Message(object):
    """
    Message Object that contains the list of signals inside
    """

    def __init__(self, mid, name, dlc, sender):
        self.mid = mid
        self.name = name
        self.dlc = dlc
        self.sender = sender
        self.signals = []

    def add_signal(self, s):
        self.signals.append(s)

    def get_struct_name(self):
        return "%s_TX_%s_t" % (self.sender, self.name)
        
    def is_recipient_of_at_least_one_sig(self, node):
        for s in self.signals:
            if node in s.recipients:
                return True
        return False


class DBC(object):
    def __init__(self, name):
        self.name = name
        self.messages = []
        self.nodes = []

    
def main(argv):
    dbcfile = ''
    self_node = ''
    gen_all = False
    
    try:
        opts, args = getopt.getopt(argv, "hi:s:a", ["ifile=", "self="])
    except getopt.GetoptError:
        print ('dbc_parse.py -i <dbcfile> -s <self_node> -all False')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('dbc_parse.py -i <dbcfile> -s <self_node> - all False')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            dbcfile = arg
        elif opt in ("-s", "--self"):
            self_node = arg
        elif opt in ("-a", "--all"):
            gen_all = True

    print ("/// DBC file: %s    Self node: %s" % (dbcfile, self_node))
    print ("/// This file should be included by a source file, for example: #include \"generated.c\"")
    print ("#include <stdbool.h>")
    print ("#include <stdint.h>")
    print ("")
    
    dbc = DBC(dbcfile)
    f = open(dbcfile, "r")
    while 1:
        line = f.readline()
        if not line:
            break

        # Nodes in the DBC file
        if line.startswith("BU_:"):
            nodes = line.strip("\n").split(' ')
            dbc.nodes = (nodes[1:])
            if self_node not in dbc.nodes:
                print ('/////////////////////////////// ERROR /////////////////////////////////////')
                print ('#error "Self node: ' + self_node + ' not found in _BU nodes in the DBC file"')
                print ('/////////////////////////////// ERROR /////////////////////////////////////')
                print ('')
            
        # Start of a message
        if line.startswith("BO_ "):
            tokens = line.split(' ')
            msg = Message(tokens[1], tokens[2].strip(":"), tokens[3], tokens[4].strip("\n"))
            dbc.messages.append(msg)

        # Signals
        if line.startswith(" SG_ "):
            t = line.split(' ')

            # Split the bit start and the bit size
            s = re.split('[|@]', t[4])
            bit_start = s[0]
            bit_size = s[1]
            is_unsigned = '+' in s[2]

            # Split (0.1,1) to two tokens by removing the ( and the )
            s = t[5][1:-1].split(',')
            scale = s[0]
            offset = s[1]

            # Split the [0|0] to min and max
            s = t[6][1:-1].split('|')
            min_val = s[0]
            max_val = s[1]

            recipients = t[8].strip('\n').split(',')

            # Add the signal the last message object
            sig = Signal(t[2], bit_start, bit_size, is_unsigned, scale, offset, min_val, max_val, recipients)
            dbc.messages[-1].add_signal(sig)
        
    # Generate message IDs
    for m in dbc.messages:
        print ("static const uint32_t " + (m.get_struct_name()[:-2] + "_MID = ").ljust(32+7) + m.mid + ";")
    print ("")
    
    # Generate message LENs
    for m in dbc.messages:
        print ("static const uint8_t " + (m.get_struct_name()[:-2] + "_DLC = ").ljust(32+7) + m.dlc + ";")
    print ("")
    
    # Generate MIA struct
    print ("typedef struct { ")
    print ("    uint32_t is_mia : 1;          ///< Missing in action flag")
    print ("    uint32_t mia_counter_ms : 31; ///< Missing in action counter")
    print ("} mia_info_t;")
        
    # Generate converted struct types for each message
    for m in dbc.messages:
        if (False == m.is_recipient_of_at_least_one_sig(self_node) and m.sender != self_node):
            print ("\n/// Not generating '" + m.get_struct_name() + "' since we are not the sender or a recipient of any of its signals")
            continue
            
        print ("\n/// Message: " + m.name + " from '" + m.sender + "', DLC: " + m.dlc + " byte(s), MID: " + m.mid)
        print ("typedef struct {")
        for s in m.signals:
            print (get_signal_code(s))
        
        print ("")
        print ("    mia_info_t mia_info;")
        print ("} " + m.get_struct_name() + ";")

    # Generate MIA handler "externs"
    print ("\n/// These 'externs' need to be defined in a source file of your project")
    for m in dbc.messages:
        if gen_all or m.is_recipient_of_at_least_one_sig(self_node):
            print ("extern const uint32_t " + m.name + "__MIA_MS;")
            print ("extern const " + m.get_struct_name() + " " + m.name + "__MIA_MSG;")
            
    # Generate marshal methods
    for m in dbc.messages:
        if not gen_all and m.sender != self_node:
            print ("\n/// Not generating code for " + m.get_struct_name()[:-2] + "_encode() since the sender is " + m.sender + " and we are " + self_node)
            continue

        print ("\n/// Encode " + m.sender + "'s '" + m.name + "' message")
        print ("/// @returns the DLC that should be used for this message")
        print ("static uint8_t " + m.get_struct_name()[:-2] + "_encode(uint64_t *to, " + m.get_struct_name() + " *from)")
        print ("{")
        print ("    *to = 0; ///< Default the entire destination data with zeroes")
        print ("")
        
        for s in m.signals:
            # Min/Max check
            if s.min_val != 0 or s.max_val != 0:
                print ("\n    if(from->" + s.name + " < " + s.min_val_str + ") { " + "from->" + s.name + " = " + s.min_val_str + "; }")
                print ("    if(from->" + s.name + " > " + s.max_val_str + ") { " + "from->" + s.name + " = " + s.max_val_str + "; }")

            # Compute binary value
            print ("    *to |= ((uint64_t) ((from->" + s.name + " - (" + s.offset_str + ")) / " + s.scale_str + " + 0.5)) << " + str(s.bit_start) + ";")
        print ("\n    return " +  m.get_struct_name()[:-2] +"_DLC;")
        print ("}")

    # Generate unmarshal methods
    for m in dbc.messages:
        if not gen_all and not m.is_recipient_of_at_least_one_sig(self_node):
            print ("\n/// Not generating code for " + m.get_struct_name()[:-2] + "_decode() since we are not the recipient of any of its signals")
            continue

        print ("\n/// Decode " + m.sender + "'s '" + m.name + "' message")
        print ("static inline bool " + m.get_struct_name()[:-2] + "_decode(" + m.get_struct_name() + " *to, const uint64_t *from, uint8_t dlc)")
        print ("{")
        print ("    const bool success = true;")
        print ("    if (dlc != " + m.get_struct_name()[:-2] + "_DLC) {");
        print ("        return !success;")
        print ("    }")
        print ("")
        for s in m.signals:
            print ("    to->" + s.name.ljust(32) + " =", end='')
            print (" (((*from >> " + str(s.bit_start).rjust(2) + ") & 0x" + format(2 ** s.bit_size - 1, '08x').ljust(7) + ")", end='')
            print (" * " + str(s.scale) + ") + (" + s.offset_str + ");")
        print ("")
        print ("    to->mia_info.mia_counter_ms = 0; ///< Reset the MIA counter")
        print ("    return success;")
        print ("}")

    # Generate MIA handler for the dbc.messages we are a recipient of
    for m in dbc.messages:
        if not gen_all and not m.is_recipient_of_at_least_one_sig(self_node):
            continue

        print ("\n/// Handle the MIA for " + m.sender + "'s '" + m.name + "' message")
        print ("/// @param   time_incr_ms  The time to increment the MIA counter with")
        print ("/// @returns true if the MIA just occurred")
        print ("/// @post    If the MIA counter is not reset, and goes beyond the MIA value, the MIA flag is set")
        print ("static inline bool " + m.get_struct_name()[:-2] + "_handle_mia(" + m.get_struct_name() + " *msg, uint32_t time_incr_ms)")
        print ("{")
        print ("    bool mia_occurred = false;")
        print ("    const mia_info_t old_mia = msg->mia_info;")
        print ("    msg->mia_info.is_mia = (msg->mia_info.mia_counter_ms >= " + m.name + "__MIA_MS);")
        print ("")
        print ("    if (!msg->mia_info.is_mia) { ")
        print ("        msg->mia_info.mia_counter_ms += time_incr_ms;")
        print ("    }")
        print ("    else if(!old_mia.is_mia)   { ")
        print ("        // Copy MIA struct, then re-write the MIA counter and is_mia that is overwriten")
        print ("        *msg = " + m.name + "__MIA_MSG;")
        print ("        msg->mia_info.mia_counter_ms = " + m.name + "__MIA_MS;")
        print ("        msg->mia_info.is_mia = true;")
        print ("        mia_occurred = true;");
        print ("    }")
        print ("\n    return mia_occurred;");
        print ("}")       
        
        
def get_signal_code(s):
    code = ""
    # code += "    " + str(s.__dict__)

    code += "    " + s.get_code_var_type() + " " + s.name + ";"

    # Align the start of the comments
    for i in range(len(code), 40):
        code += " "

    # Comment with Min/Max
    code += " ///< B" + str(s.bit_start + s.bit_size - 1) + ":" + str(s.bit_start)
    if s.min_val != 0 or s.max_val != 0:
        code += "  Min: " + s.min_val_str + " Max: " + s.max_val_str

    # Comment with destination nodes:
    code += "   Destination: "
    for r in s.recipients:
        if r == s.recipients[0]:
            code += r
        else:
            code += "," + r

    return code


if __name__ == "__main__":
    main(sys.argv[1:])

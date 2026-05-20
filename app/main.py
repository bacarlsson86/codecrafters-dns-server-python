import socket

DNS_HEADER_FIELDS = {
    "ID":      16,
    "QR":       1,
    "OPCODE":   4,
    "AA":       1,
    "TC":       1,
    "RD":       1,
    "RA":       1,
    "Z":        3,
    "RCODE":    4,
    "QDCOUNT": 16,
    "ANCOUNT": 16,
    "NSCOUNT": 16,
    "ARCOUNT": 16,
}

def parse(buf):
    raw_binary = ''.join(format(byte, '08b') for byte in buf)
    left_bit = 0
    request = {}
    for header_field, bit_length in DNS_HEADER_FIELDS.items():
        right_bit = left_bit + int(bit_length)
        print(f"Processing {header_field} as bits {left_bit} through {right_bit}")
        request[header_field] = raw_binary[left_bit: right_bit]
        print(f'{header_field} is {request[header_field]} with length {right_bit - left_bit}')
        left_bit = right_bit
    return(request)




def main():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))
    skip_first = 0
    while True:
        # ignore first packet per instructions
        if skip_first == 0:
            skip_first = 1
            continue

        try:
            buf, source = udp_socket.recvfrom(512) # buf is the raw binary, source is the address of the sender
            
            parse(buf)
            response = b""
    
            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


if __name__ == "__main__":
    main()

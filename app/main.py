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

def parse(buf:bytes) -> dict:
    print(buf)
    raw_binary = ''.join(format(byte, '08b') for byte in buf)
    left_bit = 0
    request = {}
    for header_field, bit_length in DNS_HEADER_FIELDS.items():
        right_bit = left_bit + int(bit_length)
        # print(f"Processing {header_field} as bits {left_bit} through {right_bit}")
        if bit_length == 1:
            request[header_field] = bool(int(raw_binary[left_bit:right_bit]))
        else:
            request[header_field] = int(raw_binary[left_bit: right_bit],2)
        # print(f'{header_field} is {request[header_field]} with length {right_bit - left_bit}')
        left_bit = right_bit
    # print(request)
    return(request)

def handle(request: dict) -> dict:
    response = {}
    for header_field, value in request.items():
        if header_field == 'ID':
            response[header_field] = value
        elif header_field =='QR' or header_field == 'QDCOUNT':
            response[header_field] = 1
        else:
            response[header_field] = 0
    return response

def serialize(response: dict) -> bytes:
    total = 0
    for header_field, value in response.items():
        bit_length = DNS_HEADER_FIELDS[header_field]
        total = (total << bit_length) | value
    return total.to_bytes(12, byteorder='big')

def main():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))
    skip_first = 0
    count = 0
    while True:
        count += 1
        print(f'Processing message {count}')
        # ignore first packet per instructions
        if skip_first == 0:
            print('Skipping first message')
            skip_first = 1
            continue

        try:
            buf, source = udp_socket.recvfrom(512) # buf is the raw binary, source is the address of the sender
            
            response = serialize(handle(parse(buf))) + buf[12:]
            print(f'Sending {response}')
            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


if __name__ == "__main__":
    main()

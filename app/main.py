import socket

# in bit length
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

# in byte length
DNS_QUESTION_FIELDS = {
    "A": 2,
    "IN": 2
}

# in bit length
# total bytes 14
DNS_ANSWER_FIELDS = {
    "TYPE": 16,
    "CLASS": 16,
    "TTL": 32,
    "LENGTH": 16,
    "DATA": 32
}

def parse(buf:bytes) -> dict:
    # print(request)
    # make a request object of the format:
    # {headers: dict, question: dict, label_sequence: binary_string}
    request = {}
    request['headers'] = parse_headers(buf)
    request['question'], request['raw_question'] = parse_question(buf[12:])
    return request

def parse_headers(buf:bytes) -> dict:
    # print(buf)
    raw_binary = ''.join(format(byte, '08b') for byte in buf)
    left_bit = 0
    headers = {}
    for header_field, bit_length in DNS_HEADER_FIELDS.items():
        right_bit = left_bit + int(bit_length)
        # print(f"Processing {header_field} as bits {left_bit} through {right_bit}")
        if bit_length == 1:
            headers[header_field] = bool(int(raw_binary[left_bit:right_bit]))
        else:
            headers[header_field] = int(raw_binary[left_bit: right_bit],2)
        # print(f'{header_field} is {request[header_field]} with length {right_bit - left_bit}')
        left_bit = right_bit
    return headers

def parse_question(buf:bytes) -> tuple[dict, bytes]:
    parsed_question = {}
    print(f'Now parsing question {buf}')
    word_length = int(buf[0])
    first_byte = 1
    words = []
    while word_length != 0:
        last_byte = first_byte + word_length
        words.append(buf[first_byte:last_byte].decode())
        word_length = int(buf[last_byte])
        first_byte = last_byte + 1
    # this is the label interval for the raw buffer
    # question['Name'] = '.'.join(words)
    parsed_question['Name'] = buf[0:first_byte]
    parsed_question['A'] = int.from_bytes((buf[first_byte:first_byte+2]), 'big')
    parsed_question['IN'] = int.from_bytes((buf[first_byte+2:first_byte+4]), 'big')
    end_of_question = first_byte+4
    raw_question = buf[0:end_of_question]
    print(f'Question parsed as {parsed_question}')
    print(f'End of question {raw_question}')
    return parsed_question, raw_question

def parse_question_new_method(buf:bytes) -> tuple[dict, bytes]:
    LABEL_TERMINATOR = b"\x00"
    COMPRESSION_POINTER = b"\xc0"
    parsed_question = {}
    offset = 0
    end_of_label = buf.find(LABEL_TERMINATOR) + 1
    label = buf[offset:end_of_label]
    parsed_question['Name'] = label
    parsed_question['A'] = 1
    parsed_question['IN'] = 1
    end_of_question = end_of_label + 4
    print(f'Question parsed as {parsed_question}')
    print(f'End of question {buf[0:end_of_question]}')
    return parsed_question, buf[0:end_of_question]

def handle(request:dict) -> dict:
    # request is a dict that contains a headers dict, a question dict, and a raw_question bytes value
    response = {}
    response['headers'] = handle_header(request['headers'])

    # handle question appropriately
    response['question'] = request['question']
    response['answer'] = create_answer(response['question']['Name'])
    response['raw_question'] = request['raw_question']
    return response

def handle_header(request_headers: dict) -> dict:
    response_header = {}
    for header_field, value in request_headers.items():
        if header_field == 'ID' or header_field == 'OPCODE' or header_field == 'RD':
            response_header[header_field] = value
        elif header_field =='QR' or header_field == 'QDCOUNT' or header_field == 'ANCOUNT':
            response_header[header_field] = 1
        elif header_field == 'RCODE':
            response_header[header_field] = 0 if response_header['OPCODE'] == 0 else 4
        else:
            response_header[header_field] = 0
    return response_header

def create_answer(name: str) -> bytes:
    answer_arr = []
    answer_arr.append(name)
    answer_arr.append(b'\x00\x01')  # A record = 1
    answer_arr.append(b'\x00\x01')  # IN class = 1
    answer_arr.append(b'\x00\x00\x00\x3c')  # 60 seconds
    answer_arr.append(b'\x00\x04')  # 4 bytes for IP
    answer_arr.append(b'\x08\x08\x08\x08')  # 8.8.8.8
    return b''.join(answer_arr)


def serialize(response: dict) -> bytes:
    print('Serializing')
    total = 0
    header_bytes = 12
    print('Serializing headers')
    for header_field, value in response['headers'].items():
        bit_length = DNS_HEADER_FIELDS[header_field]
        total = (total << bit_length) | value
    serialized_header = total.to_bytes(header_bytes, byteorder='big')

    print(f'header {serialized_header}')
    print(f'question {response['raw_question']}')
    print(f'answer {response['answer']}')
    return serialized_header + response['raw_question'] + response['answer']

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
            print(f'Raw request {buf}')
            response = serialize(handle(parse(buf)))
            # question is returned as received
            print(f'Sending {response}')
            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


if __name__ == "__main__":
    main()

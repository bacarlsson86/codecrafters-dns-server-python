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
    print(buf)
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
    label_sequence = buf[0:first_byte]
    # question['Name'] = '.'.join(words)
    parsed_question['Name'] = label_sequence
    parsed_question['A'] = int(buf[first_byte:first_byte+2])
    parsed_question['IN'] = int(buf[first_byte+2:first_byte+4])
    end_of_question = first_byte+4
    raw_question = buf[0:end_of_question]
    return parsed_question, raw_question

def handle_header(request_headers: dict) -> dict:
    response_header = {}
    for header_field, value in request_headers.items():
        if header_field == 'ID':
            response_header[header_field] = value
        elif header_field =='QR' or header_field == 'QDCOUNT':
            response_header[header_field] = 1
        else:
            response_header[header_field] = 0
    return response_header

def create_answer(name: str) -> dict:
    answer = {}
    answer['Name'] = name
    answer['Type'] = 1
    answer['Class'] = 1
    answer['TTL'] = 60
    answer['Length'] = 4
    answer['Data'] = b"\x08\x08\x08\x08"
    return answer

def handle(request:dict) -> dict:
    # request is a dict that contains a headers dict, a question dict, and a raw_question bytes value
    response = {}
    response['headers'] = handle_header(request['headers'])
    response['question'] = request['question']
    response['answer'] = create_answer(request['question']['Name'])
    response['raw_question'] = request['raw_question']
    return response

def serialize(response: dict) -> bytes:
    print('Serializing')
    total = 0
    total_bytes = 12
    print('Serializing headers')
    for header_field, value in response['headers'].items():
        bit_length = DNS_HEADER_FIELDS[header_field]
        total = (total << bit_length) | value
    print('Serializing question')
    total += response['raw_question']
    total_bytes += len(response['raw_question'])
    print('Serializing answer')
    for answer_field, value in response['answer'].items():
        if answer_field == 'Name':
            # do name
            name_length = len(value)
            total += value
            total_bytes += name_length
        else:
            bit_length = DNS_ANSWER_FIELDS[answer_field]
            total = (total << bit_length) | value
            total_bytes += DNS_ANSWER_FIELDS[answer_field]/2
    return total.to_bytes(total_bytes, byteorder='big')

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
            response, end_of_question, answer = handle(parse(buf))
            # question is returned as received
            response = serialize(response) + buf[12:end_of_question] + serialize(answer)
            print(f'Sending {response}')
            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


if __name__ == "__main__":
    main()

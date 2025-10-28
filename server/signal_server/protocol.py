import logging
import struct
from enum import IntEnum

# Mapeia Nomes de Comando para Códigos de Bytes
# O primeiro byte de uma msg é sempre um byte
class CommandCode(IntEnum):
    # Cliente -> Servidor
    REGISTER = 0x01; LOGIN = 0x02; GET_INITIAL_DATA = 0x03; SEARCH_USER = 0x04
    ADD_FRIEND = 0x05; ACCEPT_FRIEND = 0x06; REJECT_FRIEND = 0x07; INVITE = 0x10
    ACCEPT = 0x11; REJECT = 0x12; BYE = 0x13

    # Servidor -> Cliente
    REGISTER_RESPONSE = 0x81; LOGIN_RESPONSE = 0x82; FRIEND_LIST = 0x83
    PENDING_FRIEND_REQUESTS = 0x84; SEARCH_RESPONSE = 0x85; ADD_FRIEND_RESPONSE = 0x86
    INCOMING_FRIEND_REQUEST = 0x87; FRIEND_REQUEST_ACCEPTED = 0x88; INVITE_RESPONSE = 0x90
    INCOMING_CALL = 0x91; CALL_ACCEPTED = 0x92; CALL_REJECTED = 0x93
    CALL_ENDED = 0x94; STATUS_UPDATE = 0xA0; ERROR = 0xFF

# Mapeamento reverso 
CODE_TO_COMMAND_NAME = {v.value: k for k, v in CommandCode.__members__.items()}

# ! = Network Order, B = unsigned char (1 byte), H = unsigned short (2 bytes), ? = bool (1 byte)
FMT_HEADER = "!BH" # Command(1), PayloadSize(2)
FMT_COUNT = "!H"   # Para contagem de itens em listas (2 bytes)
FMT_BOOL = "!?"    # Para booleanos (1 byte)
FMT_PORT = "!H"    # Para números de porta (2 bytes)

# Transformar uma string Python em uma sequência de bytes
# formato definido é: [Tamanho da string em bytes (2 bytes)][String codificada em UTF-8 (N bytes)].
def serialize_string(s: str) -> bytes:
    s_bytes = (s or '').encode('utf-8')
    return struct.pack(FMT_COUNT, len(s_bytes)) + s_bytes 

def deserialize_string(buffer: bytes, offset: int) -> tuple[str, int]:
    if len(buffer) < offset + struct.calcsize(FMT_COUNT):
        raise ValueError("Buffer insuficiente para ler tamanho da string")
    str_len = struct.unpack_from(FMT_COUNT, buffer, offset)[0]
    data_offset = offset + struct.calcsize(FMT_COUNT)
    end_offset = data_offset + str_len
    if len(buffer) < end_offset:
         raise ValueError(f"Buffer insuficiente para ler string completa (necessário {str_len}, disponível {len(buffer) - data_offset} bytes)")
    s_bytes = buffer[data_offset : end_offset]
    return s_bytes.decode('utf-8') if s_bytes else '', end_offset

# Serializa uma lista de strings: Contagem (2 bytes) + Strings Serializadas
def serialize_string_list(str_list: list[str]) -> bytes:
    b = bytearray()
    b.extend(struct.pack(FMT_COUNT, len(str_list)))
    for s in str_list:
        b.extend(serialize_string(s))
    return bytes(b)

def deserialize_string_list(buffer: bytes, offset: int) -> tuple[list[str], int]:
    if len(buffer) < offset + struct.calcsize(FMT_COUNT):
        raise ValueError("Buffer insuficiente para ler contagem da lista de strings")
    count = struct.unpack_from(FMT_COUNT, buffer, offset)[0]
    current_offset = offset + struct.calcsize(FMT_COUNT)
    result_list = []
    for _ in range(count):
        s, current_offset = deserialize_string(buffer, current_offset)
        result_list.append(s)
    return result_list, current_offset


# --- Serialização de Payloads Específicos ---

def serialize_payload(command_code: CommandCode, payload: dict) -> bytes:
    b = bytearray()
    try:
        # --- Payloads Cliente -> Servidor ---
        if command_code in (CommandCode.LOGIN, CommandCode.REGISTER):
            b.extend(serialize_string(payload.get('nickname')))
            b.extend(serialize_string(payload.get('password')))
            if command_code == CommandCode.REGISTER:
                b.extend(serialize_string(payload.get('name')))
        elif command_code == CommandCode.GET_INITIAL_DATA:
            pass 
        elif command_code == CommandCode.SEARCH_USER:
             b.extend(serialize_string(payload.get('nickname_query')))
        elif command_code == CommandCode.ADD_FRIEND:
             b.extend(serialize_string(payload.get('target_nickname')))
        elif command_code in (CommandCode.ACCEPT_FRIEND, CommandCode.REJECT_FRIEND):
             b.extend(serialize_string(payload.get('requester_nickname')))
        elif command_code == CommandCode.INVITE:
             b.extend(serialize_string(payload.get('target_nickname')))
        elif command_code == CommandCode.ACCEPT:
             b.extend(serialize_string(payload.get('caller_nickname')))
        elif command_code == CommandCode.REJECT:
             b.extend(serialize_string(payload.get('caller_nickname')))
        elif command_code == CommandCode.BYE:
            pass 

        # Payloads Servidor -> Cliente
        elif command_code in (CommandCode.REGISTER_RESPONSE, CommandCode.LOGIN_RESPONSE,
                              CommandCode.ADD_FRIEND_RESPONSE, CommandCode.INVITE_RESPONSE,
                              CommandCode.ERROR):
            # Formato: success (bool) + message (string)
            b.extend(struct.pack(FMT_BOOL, payload.get('success', False)))
            b.extend(serialize_string(payload.get('message', '')))
            # Adiciona nickname para LOGIN_RESPONSE sucesso
            if command_code == CommandCode.LOGIN_RESPONSE and payload.get('success'):
                b.extend(serialize_string(payload.get('nickname')))

        elif command_code == CommandCode.FRIEND_LIST:
            # Formato: Contagem (2 bytes) + [nickname (str) + status (str)] * Contagem
            friends = payload.get('friends', [])
            b.extend(struct.pack(FMT_COUNT, len(friends)))
            for friend in friends:
                b.extend(serialize_string(friend.get('nickname')))
                b.extend(serialize_string(friend.get('status')))

        elif command_code == CommandCode.PENDING_FRIEND_REQUESTS:
            # Formato: Lista de Strings (requesters)
            b.extend(serialize_string_list(payload.get('requests_from', [])))

        elif command_code == CommandCode.SEARCH_RESPONSE:
            # Formato: success (bool) + Contagem (2 bytes) + [nickname (str) + name (str)] * Contagem
            results = payload.get('results', [])
            b.extend(struct.pack(FMT_BOOL, payload.get('success', True))) # Assume sucesso se há resultados
            b.extend(struct.pack(FMT_COUNT, len(results)))
            for user in results:
                b.extend(serialize_string(user.get('nickname')))
                b.extend(serialize_string(user.get('name')))

        elif command_code == CommandCode.INCOMING_FRIEND_REQUEST:
            # Formato: from_nickname (string)
             b.extend(serialize_string(payload.get('from_nickname')))

        elif command_code == CommandCode.FRIEND_REQUEST_ACCEPTED:
            # Formato: by_nickname (string) + status (string)
            b.extend(serialize_string(payload.get('by_nickname')))
            b.extend(serialize_string(payload.get('status')))

        elif command_code == CommandCode.INCOMING_CALL:
            # Formato: from_nickname (string)
            b.extend(serialize_string(payload.get('from_nickname')))

        elif command_code == CommandCode.CALL_ACCEPTED:
            # Formato: callee_nickname (str) + relay_ip (str) + relay_port (H) + token (str)
            b.extend(serialize_string(payload.get('callee_nickname'))) 
            b.extend(serialize_string(payload.get('relay_ip')))
            b.extend(struct.pack(FMT_PORT, payload.get('relay_port', 0)))
            b.extend(serialize_string(payload.get('token')))

        elif command_code == CommandCode.CALL_REJECTED:
            # Formato: callee_nickname (string)
            b.extend(serialize_string(payload.get('callee_nickname')))

        elif command_code == CommandCode.CALL_ENDED:
            # Formato: from_nickname (string)
            b.extend(serialize_string(payload.get('from_nickname')))

        elif command_code == CommandCode.STATUS_UPDATE:
            # Formato: nickname (string) + status (string)
            b.extend(serialize_string(payload.get('nickname')))
            b.extend(serialize_string(payload.get('status')))

        else:
             raise NotImplementedError(f"Serialização não implementada para o comando: {command_code.name}")

        return bytes(b)

    except (struct.error, TypeError, KeyError, AttributeError) as e:
        cmd_name = CODE_TO_COMMAND_NAME.get(command_code, f"UNKNOWN(0x{command_code.value:02X})")
        logging.error(f"Erro ao serializar payload para {cmd_name}: {e}. Payload: {payload}", exc_info=True)
        # Retorna um payload de erro genérico se a serialização falhar
        error_payload = {'success': False, 'message': 'Erro interno do servidor ao serializar resposta.'}
        b_error = bytearray()
        b_error.extend(struct.pack(FMT_BOOL, error_payload['success']))
        b_error.extend(serialize_string(error_payload['message']))
        return bytes(b_error) # Retorna payload de erro serializado

# --- Função de Criação de Mensagem (sem mudança) ---
def create_message(command_code: CommandCode, payload_bytes: bytes) -> bytes:
    """Cria a mensagem completa: Comando(1) + Tamanho(2) + Payload(N)"""
    header = struct.pack(FMT_HEADER, command_code.value, len(payload_bytes))
    return header + payload_bytes

# --- Desserialização de Payloads Específicos ---

def deserialize_payload(command_code: CommandCode, payload_bytes: bytes) -> dict:
    """Desserializa os bytes do payload para um dicionário, baseado no comando."""
    payload = {}
    offset = 0
    try:
        # --- Payloads Cliente -> Servidor ---
        if command_code in (CommandCode.LOGIN, CommandCode.REGISTER):
            payload['nickname'], offset = deserialize_string(payload_bytes, offset)
            payload['password'], offset = deserialize_string(payload_bytes, offset)
            if command_code == CommandCode.REGISTER:
                payload['name'], offset = deserialize_string(payload_bytes, offset)
        elif command_code == CommandCode.GET_INITIAL_DATA:
            pass # Sem payload
        elif command_code == CommandCode.SEARCH_USER:
             payload['nickname_query'], offset = deserialize_string(payload_bytes, offset)
        elif command_code == CommandCode.ADD_FRIEND:
             payload['target_nickname'], offset = deserialize_string(payload_bytes, offset)
        elif command_code in (CommandCode.ACCEPT_FRIEND, CommandCode.REJECT_FRIEND):
             payload['requester_nickname'], offset = deserialize_string(payload_bytes, offset)
        elif command_code == CommandCode.INVITE:
             payload['target_nickname'], offset = deserialize_string(payload_bytes, offset)
        elif command_code == CommandCode.ACCEPT:
             payload['caller_nickname'], offset = deserialize_string(payload_bytes, offset)
        elif command_code == CommandCode.REJECT:
             payload['caller_nickname'], offset = deserialize_string(payload_bytes, offset)
        elif command_code == CommandCode.BYE:
            pass # Sem payload

        # --- Payloads Servidor -> Cliente ---
        elif command_code in (CommandCode.REGISTER_RESPONSE, CommandCode.LOGIN_RESPONSE,
                              CommandCode.ADD_FRIEND_RESPONSE, CommandCode.INVITE_RESPONSE,
                              CommandCode.ERROR):
            payload['success'] = struct.unpack_from(FMT_BOOL, payload_bytes, offset)[0]
            offset += struct.calcsize(FMT_BOOL)
            payload['message'], offset = deserialize_string(payload_bytes, offset)
            if command_code == CommandCode.LOGIN_RESPONSE and payload.get('success'):
                payload['nickname'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.FRIEND_LIST:
            count = struct.unpack_from(FMT_COUNT, payload_bytes, offset)[0]
            offset += struct.calcsize(FMT_COUNT)
            friends = []
            for _ in range(count):
                nick, offset = deserialize_string(payload_bytes, offset)
                status, offset = deserialize_string(payload_bytes, offset)
                friends.append({'nickname': nick, 'status': status})
            payload['friends'] = friends

        elif command_code == CommandCode.PENDING_FRIEND_REQUESTS:
            requests, offset = deserialize_string_list(payload_bytes, offset)
            payload['requests_from'] = requests

        elif command_code == CommandCode.SEARCH_RESPONSE:
            payload['success'] = struct.unpack_from(FMT_BOOL, payload_bytes, offset)[0]
            offset += struct.calcsize(FMT_BOOL)
            count = struct.unpack_from(FMT_COUNT, payload_bytes, offset)[0]
            offset += struct.calcsize(FMT_COUNT)
            results = []
            for _ in range(count):
                nick, offset = deserialize_string(payload_bytes, offset)
                name, offset = deserialize_string(payload_bytes, offset)
                results.append({'nickname': nick, 'name': name})
            payload['results'] = results

        elif command_code == CommandCode.INCOMING_FRIEND_REQUEST:
             payload['from_nickname'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.FRIEND_REQUEST_ACCEPTED:
            payload['by_nickname'], offset = deserialize_string(payload_bytes, offset)
            payload['status'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.INCOMING_CALL:
            payload['from_nickname'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.CALL_ACCEPTED:
            payload['callee_nickname'], offset = deserialize_string(payload_bytes, offset)
            payload['relay_ip'], offset = deserialize_string(payload_bytes, offset)
            payload['relay_port'] = struct.unpack_from(FMT_PORT, payload_bytes, offset)[0]
            offset += struct.calcsize(FMT_PORT)
            payload['token'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.CALL_REJECTED:
            payload['callee_nickname'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.CALL_ENDED:
            payload['from_nickname'], offset = deserialize_string(payload_bytes, offset)

        elif command_code == CommandCode.STATUS_UPDATE:
            payload['nickname'], offset = deserialize_string(payload_bytes, offset)
            payload['status'], offset = deserialize_string(payload_bytes, offset)

        else:
             raise NotImplementedError(f"Desserialização não implementada para o comando: {command_code.name}")

        # Verifica se todos os bytes foram consumidos (importante!)
        if offset != len(payload_bytes):
            logging.warning(f"Bytes extras no payload para comando {command_code.name}. Esperado: {offset}, Recebido: {len(payload_bytes)}")
            # Dependendo da robustez desejada, pode-se levantar um erro aqui ou apenas logar.

        return payload

    except (ValueError, struct.error, IndexError, KeyError, AttributeError) as e:
        cmd_name = CODE_TO_COMMAND_NAME.get(command_code, f"UNKNOWN(0x{command_code.value:02X})")
        data_preview = payload_bytes[:50].hex() + ('...' if len(payload_bytes)>50 else '')
        logging.error(f"Falha ao desserializar payload BINÁRIO para comando {cmd_name}: {e}. Buffer(hex): {data_preview}", exc_info=True)
        return {"error": "Falha na desserialização do payload binário"}
    except Exception as e: # Captura outros erros
        cmd_name = CODE_TO_COMMAND_NAME.get(command_code, f"UNKNOWN(0x{command_code.value:02X})")
        logging.error(f"Erro inesperado ao desserializar payload para {cmd_name}: {e}", exc_info=True)
        return {"error": "Erro inesperado na desserialização do payload"}
# python3 -m server.signal_server.testes.teste_stream_file
# python3 -m server.signal_server.testes.teste_stream_tcp
# python3 -m server.signal_server.testes.teste_stream_tcp

import io
import struct
from typing import List, BinaryIO, Optional
from ..models.UserRecord import UserRecord 

FMT_COUNT = "!H"

class UserRecordOutputStream(io.BufferedIOBase):
    """
    Subclasse de OutputStream para escrever um array de UserRecord
    em um formato binário.

    Formato:   [Num Objetos (H)]:
               [Tam Nick (H)][Nick Bytes]
               [Tam Name (H)][Name Bytes]
               [Tam Desc (H)][Desc Bytes]
    """
    def __init__(self, records_array: List[UserRecord], num_objects_to_send: int, dest_stream: BinaryIO): 
        """
        Construtor[cite: 9, 10, 11].
        :param records_array: Array de objetos UserRecord[cite: 9].
        :param num_objects_to_send: Número de objetos a enviar[cite: 10].
        :param dest_stream: OutputStream de destino.
        """
        super().__init__()
        # Garante que não tentaremos enviar mais objetos do que existem no array
        self.num_objects_to_send = min(num_objects_to_send, len(records_array))
        self.records_to_send = records_array[:self.num_objects_to_send]
        self.dest_stream = dest_stream
        self._buffer = bytearray() # Buffer interno para escrita

        self._serialize_all()

    def _serialize_string(self, s: str) -> bytes:
        """Serializa string: Tamanho (!H) + UTF-8 bytes"""
        s_bytes = (s or '').encode('utf-8')
        return struct.pack(FMT_COUNT, len(s_bytes)) + s_bytes

    def _serialize_record(self, record: UserRecord) -> bytes:
        """Serializa um UserRecord (nickname, name, description)."""
        nick_bytes = self._serialize_string(record.nickname)
        name_bytes = self._serialize_string(record.name)
        desc_bytes = self._serialize_string(record.description)
        # Concatena os 3 atributos serializados
        return nick_bytes + name_bytes + desc_bytes

    def _serialize_all(self):
        """Serializa o número de objetos e todos os registros no buffer."""
        self._buffer.extend(struct.pack(FMT_COUNT, self.num_objects_to_send))
        # Para cada objeto, serializa os 3 atributos com seus tamanhos 
        for record in self.records_to_send:
            self._buffer.extend(self._serialize_record(record))

    def write(self, b: bytes = None) -> int:
        """
        Escreve os dados do buffer interno para o stream de destino[cite: 7].
        O argumento 'b' é ignorado.
        """
        if not self._buffer:
            return 0
        try:
            written = self.dest_stream.write(self._buffer)
            if hasattr(self.dest_stream, 'flush'):
                 self.dest_stream.flush()
            if written == len(self._buffer):
                 bytes_written = len(self._buffer)
                 self._buffer = bytearray()
                 return bytes_written
            elif written > 0:
                 print(f"Alerta: Escrita parcial detectada ({written}/{len(self._buffer)})")
                 self._buffer = self._buffer[written:]
                 return written
            else:
                 print("Alerta: write() retornou 0 bytes escritos.")
                 return 0 

        except Exception as e:
            print(f"Erro ao escrever no stream de destino: {e}")
            self._buffer = bytearray() 
            raise

    def readable(self) -> bool: return False
    def seekable(self) -> bool: return False
    def writable(self) -> bool: return True


class UserRecordInputStream(io.BufferedIOBase):

    def __init__(self, source_stream: BinaryIO): 

        super().__init__()
        self.source_stream = source_stream
        self.num_objects = -1 # Número total de objetos no stream 
        self.objects_read = 0 # Contador de objetos já lidos

    def _read_exact(self, num_bytes: int) -> bytes:
        """Lê exatamente num_bytes do stream de origem."""
        data = self.source_stream.read(num_bytes)
        if data is None: raise EOFError("Stream retornou None.")
        if len(data) < num_bytes:
            raise EOFError(f"Fim inesperado. Esperava {num_bytes}, obteve {len(data)}.")
        return data

    def _deserialize_string(self) -> str:
        """Lê Tamanho (!H) + UTF-8 bytes do stream."""
        size_bytes = self._read_exact(struct.calcsize(FMT_COUNT))
        str_len = struct.unpack(FMT_COUNT, size_bytes)[0]
        if str_len == 0: return ""
        s_bytes = self._read_exact(str_len)
        return s_bytes.decode('utf-8')

    def read_next_record(self) -> Optional[UserRecord]:
        """
        Lê e desserializa o próximo UserRecord do stream.
        Retorna None se todos os objetos já foram lidos.
        """
        # Lê a contagem total na primeira chamada
        if self.num_objects == -1:
            try:
                count_bytes = self._read_exact(struct.calcsize(FMT_COUNT))
                self.num_objects = struct.unpack(FMT_COUNT, count_bytes)[0]
                if self.num_objects == 0:
                     return None # Não há objetos a ler
            except EOFError:
                # Se não conseguir ler nem a contagem, stream está vazio/inválido
                self.num_objects = 0
                return None

        # Verifica se já leu todos os objetos declarados
        if self.objects_read >= self.num_objects:
            return None # Fim dos dados esperados

        # Tenta ler os 3 atributos do próximo objeto 
        try:
            nickname = self._deserialize_string()
            name = self._deserialize_string()
            description = self._deserialize_string()

            record = UserRecord(nickname=nickname, name=name, description=description)
            self.objects_read += 1
            return record
        except EOFError:
            print(f"Aviso: Fim do stream alcançado antes de ler o registro #{self.objects_read + 1}. Esperava {self.num_objects} registros no total.")
            # Marca como se todos tivessem sido lidos para parar futuras tentativas
            self.objects_read = self.num_objects
            return None
        except Exception as e:
            print(f"Erro ao desserializar registro #{self.objects_read + 1}: {e}")
            self.objects_read = self.num_objects # Pára a leitura em caso de erro
            raise # Re-levanta a exceção

    def read_all_records(self) -> List[UserRecord]:
        """Lê todos os UserRecord restantes do stream."""
        records = []
        while True:
            record = self.read_next_record()
            if record is None:
                break
            records.append(record)
        return records

    def readable(self) -> bool: return True
    def seekable(self) -> bool: return False
    def writable(self) -> bool: return False

    def read(self, size: int = -1) -> bytes:
        return self.source_stream.read(size)
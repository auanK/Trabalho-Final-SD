import io
import struct
from typing import List, BinaryIO, Optional
from user_record import UserRecord 

FMT_COUNT = "!H"

class UserRecordOutputStream(io.BufferedIOBase):
    # Construtor (Q2.a)
    def __init__(self, records_array: List[UserRecord], num_objects_to_send: int, dest_stream: BinaryIO): 
        super().__init__()
        self.num_objects_to_send = min(num_objects_to_send, len(records_array))
        self.records_to_send = records_array[:self.num_objects_to_send]
        self.dest_stream = dest_stream
        self._buffer = bytearray() 
        self._serialize_all()

    def _serialize_string(self, s: str) -> bytes:
        s_bytes = (s or '').encode('utf-8')
        return struct.pack(FMT_COUNT, len(s_bytes)) + s_bytes

    def _serialize_record(self, record: UserRecord) -> bytes:
        nick_bytes = self._serialize_string(record.nickname)
        name_bytes = self._serialize_string(record.name)
        desc_bytes = self._serialize_string(record.description)
        return nick_bytes + name_bytes + desc_bytes

    def _serialize_all(self):
        self._buffer.extend(struct.pack(FMT_COUNT, self.num_objects_to_send))
        for record in self.records_to_send:
            self._buffer.extend(self._serialize_record(record))

    def write(self, b: bytes = None) -> int:
        if not self._buffer:
            return 0
        try:
            written = self.dest_stream.write(self._buffer)
            if hasattr(self.dest_stream, 'flush'):
                self.dest_stream.flush()
            
            if written is None: 
                bytes_written = len(self._buffer)
                self._buffer = bytearray()
                return bytes_written
                
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
    # Construtor (Q3.a)
    def __init__(self, source_stream: BinaryIO): 
        super().__init__()
        self.source_stream = source_stream
        self.num_objects = -1 
        self.objects_read = 0 

    def _read_exact(self, num_bytes: int) -> bytes:
        data = self.source_stream.read(num_bytes)
        if data is None: 
            raise EOFError("Stream retornou None durante a leitura.")
        if len(data) < num_bytes:
            raise EOFError(f"Fim inesperado do stream. Esperava {num_bytes}, obteve {len(data)}.")
        return data

    def _deserialize_string(self) -> str:
        size_bytes = self._read_exact(struct.calcsize(FMT_COUNT))
        str_len = struct.unpack(FMT_COUNT, size_bytes)[0]
        if str_len == 0: 
            return ""
        s_bytes = self._read_exact(str_len)
        return s_bytes.decode('utf-8')

    def read_next_record(self) -> Optional[UserRecord]:
        if self.num_objects == -1:
            try:
                count_bytes = self._read_exact(struct.calcsize(FMT_COUNT))
                self.num_objects = struct.unpack(FMT_COUNT, count_bytes)[0]
                if self.num_objects == 0:
                    return None 
            except EOFError:
                self.num_objects = 0
                return None 

        if self.objects_read >= self.num_objects:
            return None

        try:
            nickname = self._deserialize_string()
            name = self._deserialize_string()
            description = self._deserialize_string()

            record = UserRecord(nickname=nickname, name=name, description=description)
            self.objects_read += 1
            return record
        except EOFError:
            print(f"Aviso: Fim do stream antes de ler o registro #{self.objects_read + 1}. Esperava {self.num_objects}.")
            self.objects_read = self.num_objects
            return None
        except Exception as e:
            print(f"Erro ao desserializar registro #{self.objects_read + 1}: {e}")
            self.objects_read = self.num_objects
            raise

    def read_all_records(self) -> List[UserRecord]:
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
# Teste Q2.b.i

import sys
from user_record import UserRecord
from stream_classes import UserRecordOutputStream

records_to_write = [
    UserRecord(nickname="auank", name="Teste", description="Testando"),
]

# Teste 2.b.i: Escreve 1 objeto na Saída Padrão (System.out).
def test_write_to_stdout():
    print("Teste 2.b.i: Escrevendo em System.out")
    print("O output binário começará após esta linha:")
    
    dest_stream = sys.stdout.buffer
    out_stream = UserRecordOutputStream(
        records_array=records_to_write,
        num_objects_to_send=1,
        dest_stream=dest_stream
    )
    
    bytes_written = out_stream.write()
    
    print(f"\n Fim do Teste", file=sys.stderr)
    print(f"Total de bytes escritos no stdout: {bytes_written}", file=sys.stderr)

if __name__ == "__main__":
    test_write_to_stdout()
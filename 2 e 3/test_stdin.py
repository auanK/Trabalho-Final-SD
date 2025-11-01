# Teste Q3.b
import sys
from stream_classes import UserRecordInputStream

# Teste Q3.b: Lê objetos do System.in.
def test_read_from_stdin():
    print("Teste 3.b: Lendo de System.in")
    print("(Aguardando dados binários via pipe...)\n")
    
    source_stream = sys.stdin.buffer
    
    try:
        in_stream = UserRecordInputStream(source_stream=source_stream)
        records_read = in_stream.read_all_records()
        
        print(f"Registros lidos ({len(records_read)}):")
        for rec in records_read:
            print(f"  -> {rec}")
            
        if not records_read:
            print("Nenhum dado recebido. Use um pipe para enviar dados.")
            print("Exemplo: python test_stdout.py | python test_stdin.py")
            
    except Exception as e:
        print(f"Erro ao ler do stdin: {e}", file=sys.stderr)

if __name__ == "__main__":
    test_read_from_stdin()
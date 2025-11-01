# Teste Q2.b.ii e Q3.c
import os
from user_record import UserRecord
from stream_classes import UserRecordOutputStream, UserRecordInputStream

records_to_write = [
    UserRecord(nickname="auank", name="Kauan", description="lala"),
    UserRecord(nickname="teste", name="Teste", description="Testando"),
    UserRecord(nickname="a", name="b", description="c")
]
TEST_FILE_NAME = "test_data.bin"

# Teste Q2.b.ii: Escreve 2 dos 3 objetos em um FileOutputStream.
def test_write_to_file():
    print("Teste 2.b.ii: Escrevendo em Arquivo (FileOutputStream)")
    
    with open(TEST_FILE_NAME, "wb") as f_out:
        num_to_send = 2
        print(f"Enviando {num_to_send} de {len(records_to_write)} registros para {TEST_FILE_NAME}...")
        
        out_stream = UserRecordOutputStream(
            records_array=records_to_write,
            num_objects_to_send=num_to_send,
            dest_stream=f_out
        )
        
        bytes_written = out_stream.write()
        print(f"Total de bytes escritos no arquivo: {bytes_written}")
        
    print(f"Arquivo '{TEST_FILE_NAME}' criado.\n")

# Teste Q3.c: Lê os objetos de um FileInputStream.
def test_read_from_file():
    print("Teste 3.c: Lendo de Arquivo (FileInputStream)")
    
    if not os.path.exists(TEST_FILE_NAME):
        print(f"Erro: Arquivo '{TEST_FILE_NAME}' não encontrado.")
        return

    with open(TEST_FILE_NAME, "rb") as f_in:
        print(f"Lendo registros de {TEST_FILE_NAME}...")
        
        in_stream = UserRecordInputStream(source_stream=f_in)
        
        records_read = in_stream.read_all_records()
        
        print(f"\nRegistros lidos ({len(records_read)}):")
        for rec in records_read:
            print(f"  -> {rec}")
            
    assert len(records_read) == 2 
    assert records_read[0].nickname == "auank"
    assert records_read[1].nickname == "teste"
    print("\nVerificação: Sucesso! Dados lidos correspondem aos dados escritos.")
    

if __name__ == "__main__":
    test_write_to_file()
    test_read_from_file()

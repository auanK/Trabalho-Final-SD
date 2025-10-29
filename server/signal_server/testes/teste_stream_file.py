import os

from ..models.UserRecord import UserRecord 
from .custom_streams import UserRecordInputStream, UserRecordOutputStream

# Dados de Exemplo
records_to_send = [
    UserRecord(nickname="file_user_1", name="Arquivo Teste", description="Primeiro registro"),
    UserRecord(nickname="file_user_2", name="Outro Nome", description="Segundo registro no arquivo"),
]
num_to_send = len(records_to_send)
filename = "user_records.bin"

print("--- Teste ARQUIVO ---")

print(f"\nEscrevendo {num_to_send} registros para '{filename}'...")
try:
    with open(filename, "wb") as f_out: # 'wb' para escrita binária
        output_stream = UserRecordOutputStream(records_to_send, num_to_send, f_out)
        bytes_written = output_stream.write()
        print(f"Escrita para arquivo concluída: {bytes_written} bytes.")
except Exception as e:
    print(f"Erro durante escrita para arquivo: {e}")

print(f"\nLendo registros do arquivo '{filename}'...")
read_records = []
if os.path.exists(filename):
    try:
        with open(filename, "rb") as f_in: # 'rb' para leitura binária
            input_stream = UserRecordInputStream(f_in)
            read_records = input_stream.read_all_records()
    except Exception as e:
        print(f"Erro durante leitura do arquivo: {e}")
else:
    print(f"Arquivo '{filename}' não encontrado.")

print("\nRegistros lidos do Arquivo:")
if read_records:
    for i, record in enumerate(read_records):
        print(f"  {i+1}: {record}")
else:
    print("  Nenhum registro lido.")

# Limpeza
try:
    if os.path.exists(filename): os.remove(filename)
except Exception as e: print(f"Erro ao remover {filename}: {e}")

print("\n--- Fim do Teste ARQUIVO ---")
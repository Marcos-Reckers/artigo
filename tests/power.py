import pandas as pd
from scipy.integrate import trapezoid
import numpy as np
import os # Importado para verificar se o arquivo existe

def calcular_consumo_gpu(caminho_csv, coluna_timestamp, coluna_potencia):
    """
    Calcula o consumo de energia da GPU a partir de um arquivo CSV.

    A função realiza uma integração discreta da potência (em Watts) pelo
    tempo (em segundos) para obter a energia total consumida (em Joules) e, em
    seguida, converte o resultado para kWh.

    Args:
        caminho_csv (str): O caminho para o arquivo CSV.
        coluna_timestamp (str): O nome da coluna que contém o timestamp.
        coluna_potencia (str): O nome da coluna que contém a potência em Watts.

    Returns:
        dict: Um dicionário com os resultados ou uma mensagem de erro.
    """
    try:
        # Lê o arquivo CSV. O separador '\s*,\s*' lida com vírgulas
        # rodeadas por espaços. O 'engine='python'' é necessário para isso.
        df = pd.read_csv(caminho_csv, sep=r'\s*,\s*', engine='python')

        # Verifica se as colunas especificadas existem
        if coluna_timestamp not in df.columns or coluna_potencia not in df.columns:
            return {"erro": f"Colunas '{coluna_timestamp}' ou '{coluna_potencia}' não encontradas."}

        # Remove linhas com valores nulos nas colunas de interesse
        df.dropna(subset=[coluna_timestamp, coluna_potencia], inplace=True)

        # Converte a coluna de timestamp para o formato datetime
        df[coluna_timestamp] = pd.to_datetime(df[coluna_timestamp])

        # Ordena os dados pelo tempo para garantir a ordem correta na integração
        df.sort_values(by=coluna_timestamp, inplace=True)
        
        # Converte os timestamps para um valor numérico (segundos desde a epoch)
        tempo_em_segundos = df[coluna_timestamp].astype(np.int64) / 10**9
        
        # Pega os valores de potência
        potencia_em_watts = df[coluna_potencia].to_numpy()

        if len(tempo_em_segundos) < 2:
            return {"erro": "Pontos de dados insuficientes para realizar o cálculo (mínimo 2)."}

        # Calcula a duração total do intervalo em segundos
        tempo_total_segundos = tempo_em_segundos.iloc[-1] - tempo_em_segundos.iloc[0]

        # Realiza a integração discreta da Potência (W) em relação ao Tempo (s)
        energia_em_joules = trapezoid(y=potencia_em_watts, x=tempo_em_segundos)

        # Converte a energia de Joules para kilowatt-hora (kWh)
        energia_em_kwh = energia_em_joules / 3.6e6

        return {
            "tempo_total_segundos": tempo_total_segundos,
            "consumo_joules": energia_em_joules,
            "consumo_kwh": energia_em_kwh
        }

    except FileNotFoundError:
        return {"erro": f"Arquivo não encontrado em: {caminho_csv}"}
    except Exception as e:
        return {"erro": f"Ocorreu um erro inesperado: {e}"}

def salvar_relatorio_md(resultados, arquivo_analisado, arquivo_saida):
    """
    Salva os resultados da análise em um arquivo Markdown bem formatado.

    Args:
        resultados (dict): O dicionário com os resultados do cálculo.
        arquivo_analisado (str): O nome do arquivo CSV que foi analisado.
        arquivo_saida (str): O nome do arquivo .md a ser criado.
    """
    # Formata os números para exibição
    tempo = f"{resultados['tempo_total_segundos']:.2f}"
    joules = f"{resultados['consumo_joules']:.2f}"
    kwh = f"{resultados['consumo_kwh']:.8f}"

    conteudo_md = f"""
# 📊 Relatório de Consumo de Energia da GPU

Este relatório detalha o consumo de energia calculado a partir dos dados de monitoramento.

- **Arquivo Analisado:** `{arquivo_analisado}`
- **Data da Análise:** {pd.Timestamp.now('America/Sao_Paulo').strftime('%Y-%m-%d %H:%M:%S %Z')}

---

## Resultados da Análise

- **⏱️ Intervalo de Tempo Total:**
  - `{tempo} segundos`

- **⚡ Consumo de Energia em Joules:**
  - `{joules} J`

- **💡 Consumo de Energia em Kilowatt-hora:**
  - `{kwh} kWh`

"""
    try:
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            f.write(conteudo_md)
        print(f"✅ Relatório salvo com sucesso em: '{arquivo_saida}'")
    except Exception as e:
        print(f"❌ Erro ao salvar o relatório: {e}")


# --- Bloco de Execução Principal ---
if __name__ == '__main__':
    # 1. CONFIGURE AQUI: Altere o nome do arquivo para o seu CSV.
    #    Certifique-se de que o script e o seu CSV estão na mesma pasta,
    #    ou forneça o caminho completo (ex: 'C:/Users/Usuario/Documentos/meu_log.csv').
    arquivo_csv_entrada = '/home/lab211/artigo/tests/2060/qwen3/system_metrics.csv'

    arquivo_md_saida = 'relatorio_consumo.md'
    
    # Verifique se os nomes das colunas abaixo correspondem exatamente
    # aos cabeçalhos do seu arquivo CSV.
    coluna_timestamp = 'Timestamp'
    coluna_potencia = 'GPU Power (W)'

    # 2. Verificação da existência do arquivo de entrada
    if not os.path.exists(arquivo_csv_entrada):
        print(f"❌ ERRO: O arquivo '{arquivo_csv_entrada}' não foi encontrado.")
        print("👉 Por favor, altere a variável 'arquivo_csv_entrada' no script para o nome correto do seu arquivo.")
    else:
        print(f"📄 Analisando o arquivo: '{arquivo_csv_entrada}'...")
        
        # 3. Chama a função de cálculo
        resultados = calcular_consumo_gpu(arquivo_csv_entrada, coluna_timestamp, coluna_potencia)

        # 4. Processa os resultados
        if "erro" in resultados:
            print(f"❌ Erro ao processar o arquivo: {resultados['erro']}")
        else:
            print("Análise concluída. Gerando relatório...")
            # Salva o relatório formatado em Markdown
            salvar_relatorio_md(resultados, arquivo_csv_entrada, arquivo_md_saida)
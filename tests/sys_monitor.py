\
import psutil
import pynvml
import time
import datetime
import csv
import os
import matplotlib.pyplot as plt
import pandas as pd

# --- Configurações ---
OUTPUT_DIR = 'monitoring_results'
CSV_FILENAME = os.path.join(OUTPUT_DIR, 'system_metrics.csv')
PLOTS_DIR = os.path.join(OUTPUT_DIR, 'plots')
MONITORING_INTERVAL = 1  # segundos

# --- Inicialização ---


def initialize_pynvml():
    """Inicializa o pynvml."""
    try:
        pynvml.nvmlInit()
        return True
    except pynvml.NVMLError as e:
        print(
            f"Erro ao inicializar pynvml: {e}. As métricas da GPU NVIDIA não estarão disponíveis.")
        return False


def get_gpu_handles(pynvml_initialized):
    """Obtém os handles das GPUs NVIDIA."""
    if not pynvml_initialized:
        return []
    try:
        gpu_handles = []
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            gpu_handles.append(handle)
        return gpu_handles
    except pynvml.NVMLError as e:
        print(f"Erro ao obter handles da GPU: {e}")
        return []

# --- Funções de Coleta de Métricas ---


def get_cpu_usage():
    """Coleta o uso de CPU (%)."""
    return psutil.cpu_percent(interval=None)


def get_ram_metrics():
    """Coleta o uso de RAM (%)."""
    ram = psutil.virtual_memory()
    return ram.percent


def get_gpu_metrics_nvidia(gpu_handles):
    """Coleta o uso de GPU (%), VRAM (%) e potência da GPU (W) para GPUs NVIDIA."""
    if not gpu_handles:
        return None, None, None
    handle = gpu_handles[0]
    try:
        gpu_utilization = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
        memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_usage_percent = (
            memory_info.used / memory_info.total) * 100 if memory_info.total > 0 else 0
        gpu_power = None
        try:
            gpu_power = pynvml.nvmlDeviceGetPowerUsage(
                handle) / 1000.0  # Watts
        except pynvml.NVMLError:
            pass
        return gpu_utilization, vram_usage_percent, gpu_power
    except pynvml.NVMLError as e:
        print(f"Erro ao coletar métricas da GPU NVIDIA: {e}")
        return None, None, None

# --- Lógica de Monitoramento Contínuo ---


def monitor_continuous(csv_writer, pynvml_initialized, gpu_handles):
    print(f"Iniciando monitoramento contínuo. Pressione Ctrl+C para parar e gerar gráficos.")
    try:
        while True:
            timestamp = datetime.datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S.%f')[:-3]
            cpu_usage = get_cpu_usage()
            ram_usage = get_ram_metrics()
            gpu_usage, vram_usage, gpu_power = None, None, None
            if pynvml_initialized and gpu_handles:
                gpu_usage, vram_usage, gpu_power = get_gpu_metrics_nvidia(
                    gpu_handles)
            row = {
                'Timestamp': timestamp,
                'CPU Usage (%)': f"{cpu_usage:.2f}" if cpu_usage is not None else '',
                'RAM Usage (%)': f"{ram_usage:.2f}" if ram_usage is not None else '',
                'GPU Usage (%)': f"{gpu_usage:.2f}" if gpu_usage is not None else '',
                'VRAM Usage (%)': f"{vram_usage:.2f}" if vram_usage is not None else '',
                'GPU Power (W)': f"{gpu_power:.2f}" if gpu_power is not None else ''
            }
            csv_writer.writerow(row)
            time.sleep(MONITORING_INTERVAL)
    except KeyboardInterrupt:
        print("\nMonitoramento interrompido pelo usuário.")

# --- Geração de Gráficos ---


def generate_plots(csv_filepath):
    """Gera gráficos a partir do arquivo CSV."""
    if not os.path.exists(csv_filepath):
        print(
            f"Arquivo CSV {csv_filepath} não encontrado. Não é possível gerar gráficos.")
        return

    try:
        df = pd.read_csv(csv_filepath)
    except pd.errors.EmptyDataError:
        print(
            f"Arquivo CSV {csv_filepath} está vazio. Não é possível gerar gráficos.")
        return
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV para gráficos: {e}")
        return

    if df.empty:
        print("DataFrame está vazio. Não há dados para plotar.")
        return

    # Converter colunas numéricas, tratando 'N/A' e vazios
    numeric_cols = ['CPU Usage (%)', 'RAM Usage (%)',
                    'GPU Usage (%)', 'VRAM Usage (%)', 'GPU Power (W)']
    for col in numeric_cols:
        # 'coerce' transforma erros em NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['Timestamp'] = pd.to_datetime(df['Timestamp'])

    if not os.path.exists(PLOTS_DIR):
        os.makedirs(PLOTS_DIR)

    # Gráfico 1: % de uso da CPU + % de uso da RAM
    plt.figure(figsize=(15, 7))
    if 'CPU Usage (%)' in df.columns and df['CPU Usage (%)'].notna().any():
        plt.plot(df['Timestamp'], df['CPU Usage (%)'],
                 label='CPU Usage (%)', marker='.')
    if 'RAM Usage (%)' in df.columns and df['RAM Usage (%)'].notna().any():
        plt.plot(df['Timestamp'], df['RAM Usage (%)'],
                 label='RAM Usage (%)', marker='.')
    plt.title('Uso de CPU e RAM ao Longo do Tempo')
    plt.xlabel('Timestamp')
    plt.ylabel('Usage (%)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'cpu_ram_usage.png'))
    plt.close()
    print(f"Gráfico 'cpu_ram_usage.png' salvo em {PLOTS_DIR}")

    # Gráfico 2: Consumo da GPU em W
    if 'GPU Power (W)' in df.columns and df['GPU Power (W)'].notna().any():
        plt.figure(figsize=(15, 7))
        plt.plot(df['Timestamp'], df['GPU Power (W)'],
                 label='GPU Power (W)', marker='.', color='orange')
        plt.title('Potência da GPU ao Longo do Tempo')
        plt.xlabel('Timestamp')
        plt.ylabel('Potência (W)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, 'gpu_power.png'))
        plt.close()
        print(f"Gráfico 'gpu_power.png' salvo em {PLOTS_DIR}")
    else:
        print("Não há dados de potência da GPU para plotar.")

    # Gráfico 3: % de uso da VRAM
    if 'VRAM Usage (%)' in df.columns and df['VRAM Usage (%)'].notna().any():
        plt.figure(figsize=(15, 7))
        plt.plot(df['Timestamp'], df['VRAM Usage (%)'],
                 label='VRAM Usage (%)', marker='.', color='purple')
        plt.title('Uso de VRAM (%) ao Longo do Tempo')
        plt.xlabel('Timestamp')
        plt.ylabel('VRAM Usage (%)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, 'vram_usage.png'))
        plt.close()
        print(f"Gráfico 'vram_usage.png' salvo em {PLOTS_DIR}")
    else:
        print("Não há dados de uso de VRAM para plotar.")

    # Gráfico 4: % de uso da GPU sozinho
    if 'GPU Usage (%)' in df.columns and df['GPU Usage (%)'].notna().any():
        plt.figure(figsize=(15, 7))
        plt.plot(df['Timestamp'], df['GPU Usage (%)'],
                 label='GPU Usage (%)', marker='.', color='green')
        plt.title('Uso de GPU (%) ao Longo do Tempo')
        plt.xlabel('Timestamp')
        plt.ylabel('GPU Usage (%)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, 'gpu_usage.png'))
        plt.close()
        print(f"Gráfico 'gpu_usage.png' salvo em {PLOTS_DIR}")
    else:
        print("Não há dados de uso de GPU para plotar.")

# --- Função Principal ---


def main():
    """Função principal para executar o monitoramento."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    if not os.path.exists(PLOTS_DIR):
        os.makedirs(PLOTS_DIR)

    pynvml_initialized = initialize_pynvml()
    gpu_handles = get_gpu_handles(pynvml_initialized)
    if pynvml_initialized and not gpu_handles:
        print("pynvml inicializado, mas nenhuma GPU NVIDIA foi encontrada.")
    elif pynvml_initialized and gpu_handles:
        print(f"{len(gpu_handles)} GPU(s) NVIDIA encontrada(s).")

    csv_header = ['Timestamp', 'CPU Usage (%)', 'RAM Usage (%)',
                  'GPU Usage (%)', 'VRAM Usage (%)', 'GPU Power (W)']

    with open(CSV_FILENAME, 'w', newline='') as csvfile:
        csv_writer = csv.DictWriter(csvfile, fieldnames=csv_header)
        csv_writer.writeheader()

        monitor_continuous(csv_writer, pynvml_initialized, gpu_handles)

    print(f"Dados de monitoramento salvos em {CSV_FILENAME}")

    if pynvml_initialized:
        pynvml.nvmlShutdown()

    print("Gerando gráficos...")
    generate_plots(CSV_FILENAME)


if __name__ == "__main__":
    print("--- Monitor de CPU, RAM e GPU ---")
    print(f"Intervalo de monitoramento: {MONITORING_INTERVAL}s")
    print("O monitoramento será executado continuamente.")
    print("Pressione Ctrl+C no terminal para parar o monitoramento e gerar os gráficos.")
    print(f"Resultados serão salvos em: {OUTPUT_DIR}")
    print("Certifique-se de ter as bibliotecas Python necessárias instaladas:")
    print("  pip install psutil pynvml matplotlib pandas")
    print("Para métricas de GPU NVIDIA, é necessário ter os drivers NVIDIA instalados.")
    print("-" * 60)
    main()

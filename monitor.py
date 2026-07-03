import subprocess
import time
import re
from datetime import datetime, timedelta
import sys
import threading
import json
import os

# Persistent storage file paths
TASKS_FILE = "/Users/caioamaraldepieri/maestri-monitor/tasks.json"
SIGNALS_FILE = "/Users/caioamaraldepieri/maestri-monitor/signals.json"

# Workflow Terminal Roles (Change if you rename terminals)
ARCHITECT_AGENT = "Claude Code"
WORKER_AGENT = "Jarvis Codex"

# Regex patterns to extract the reset time from rate-limited terminal screens
RESET_REGEX = re.compile(r"resets\s+(\d+(?::\d+)?\s*(?:am|pm)?)\s*(?:\(([^)]+)\))?", re.IGNORECASE)
TRY_AGAIN_REGEX = re.compile(r"try\s+again\s+at\s+(\d+(?::\d+)?\s*(?:am|pm)?)", re.IGNORECASE)

# Configuration & State (Using RLock for reentrant locking safety)
state_lock = threading.RLock()
state = {
    "auto_monitor_enabled": True,
    "scheduled_resets": {},  # agent_name -> list of target_datetime
    "custom_tasks": [],      # list of dicts: {"id": int, "agents": list, "commands": dict, "time": datetime, "recurring": bool, "recur_time": str}
    "running": True,
    "task_counter": 1
}

def log(message, print_to_console=False):
    """Logs messages to a file, sends OS notifications, and outputs to the console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    
    # Write to a persistent log file
    try:
        with open("/Users/caioamaraldepieri/maestri-monitor/monitor.log", "a") as f:
            f.write(log_line + "\n")
    except Exception:
        pass
    
    if print_to_console:
        # Clear current line, print message, and restore the interactive prompt
        sys.stdout.write(f"\r\033[K{log_line}\nmaestri-monitor> ")
        sys.stdout.flush()

def notify_os(message):
    """Sends a native macOS desktop notification using AppleScript."""
    try:
        escaped_msg = message.replace('"', '\\"').replace("'", "\\'")
        cmd = ["osascript", "-e", f'display notification "{escaped_msg}" with title "Maestri Monitor"']
        subprocess.Popen(cmd)
    except Exception as e:
        log(f"Failed to send OS notification: {e}")

def get_connected_agents():
    """Runs `maestri list` and returns a list of connected agent names."""
    try:
        cmd = ["maestri", "list"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        
        agents = []
        in_connected = False
        for line in lines:
            if "Connected agents:" in line:
                in_connected = True
                continue
            if in_connected:
                match = re.search(r'-\s+name:\s*"([^"]+)"', line)
                if match:
                    agents.append(match.group(1))
                elif line.strip() and not line.startswith(" ") and not line.startswith("-"):
                    in_connected = False
        return agents
    except Exception as e:
        log(f"Error listing agents: {e}")
        return []

def get_connected_notes():
    """Runs `maestri list` and returns a list of connected note names."""
    try:
        cmd = ["maestri", "list"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        
        notes = []
        in_notes = False
        for line in lines:
            if "Connected notes" in line:
                in_notes = True
                continue
            if in_notes:
                match = re.search(r'-\s+name:\s*"([^"]+)"', line)
                if match:
                    notes.append(match.group(1))
                elif line.strip() and not line.startswith(" ") and not line.startswith("-"):
                    in_notes = False
        return notes
    except Exception as e:
        log(f"Error listing notes: {e}")
        return []

def update_canvas_note():
    """Updates the first connected canvas note with the current status of the monitor."""
    notes = get_connected_notes()
    if not notes:
        return
        
    note_name = notes[0]
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with state_lock:
        auto_enabled = state["auto_monitor_enabled"]
        resets = dict(state["scheduled_resets"])
        custom_tasks = list(state["custom_tasks"])
        
    content = []
    content.append("# 🖥️ Status do Monitor Maestri")
    content.append(f"**Última Atualização:** {now_str}")
    content.append(f"**Monitoramento Automático:** {'✅ ATIVADO' if auto_enabled else '❌ DESATIVADO'}")
    content.append("")
    
    content.append("## 🚦 Workflow de Desenvolvimento:")
    content.append(f"* **Arquiteto (Validador):** `{ARCHITECT_AGENT}`")
    content.append(f"* **Operário (Executor):** `{WORKER_AGENT}`")
    
    # Show last signal states
    try:
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, "r") as f:
                signals = json.load(f)
            
            last_worker = None
            last_arch = None
            for s in reversed(signals):
                if s["agent"] == WORKER_AGENT and not last_worker:
                    last_worker = s
                elif s["agent"] == ARCHITECT_AGENT and not last_arch:
                    last_arch = s
                    
            if last_worker:
                w_time = datetime.fromisoformat(last_worker["timestamp"]).strftime("%H:%M:%S")
                status_emoji = "✅" if last_worker["status"] == "concluido" else "⏳"
                content.append(f"* {status_emoji} Operário: `{last_worker['status']}` às {w_time}")
            if last_arch:
                a_time = datetime.fromisoformat(last_arch["timestamp"]).strftime("%H:%M:%S")
                arch_emoji = "🎉 APROVADO (Limpo)" if last_arch["status"] == "aprovado" else "❌ REPROVADO (Ajustando)"
                content.append(f"* 🛡️ Arquiteto: `{arch_emoji}` às {a_time}")
    except Exception:
        pass
    
    content.append("")
    content.append("## ⏳ Limites de Cota Ativos:")
    has_resets = False
    for agent, targets in resets.items():
        for t in targets:
            content.append(f"* **{agent}**: libera em `{t.strftime('%Y-%m-%d %H:%M:%S')}`")
            has_resets = True
    if not has_resets:
        content.append("* Nenhum limite ativo detectado.")
        
    content.append("")
    content.append("## 📅 Agendamentos Personalizados:")
    if not custom_tasks:
        content.append("* Nenhum agendamento ativo.")
    else:
        for task in custom_tasks:
            rec_str = " (Diário)" if task["recurring"] else " (Único)"
            content.append(f"* **[ID {task['id']}]**{rec_str} - Agentes: `{', '.join(task['agents'])}`")
            content.append(f"  * Executa em: `{task['time'].strftime('%Y-%m-%d %H:%M:%S')}`")
            summary_parts = []
            for agent in task["agents"]:
                cmds = task["commands"].get(agent, [])
                summary_parts.append(f"{agent}: {' -> '.join(cmds)}")
            content.append(f"  * Passos: {'; '.join(summary_parts)}")
            
    full_content = "\n".join(content)
    
    try:
        cmd = ["maestri", "note", "write", note_name, full_content]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except Exception as e:
        log(f"Failed to update canvas note '{note_name}': {e}")

def check_agent_limit(agent_name):
    """Runs `maestri check` on the agent and returns (time_str, tz_str) if limited, else None."""
    try:
        cmd = ["maestri", "check", agent_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        
        if "limit" in output.lower():
            match = RESET_REGEX.search(output)
            if match:
                time_str = match.group(1)
                tz_str = match.group(2) if match.group(2) else "local"
                return time_str, tz_str
            
            match = TRY_AGAIN_REGEX.search(output)
            if match:
                time_str = match.group(1)
                return time_str, "local"
        return None
    except Exception as e:
        log(f"Error checking agent {agent_name}: {e}")
        return None

def parse_reset_time(time_str):
    """Parses a time string like '9pm', '10:30am', '21:00' and returns (hour, minute)."""
    time_str = time_str.lower().strip()
    is_pm = "pm" in time_str
    is_am = "am" in time_str
    
    clean_time = time_str.replace("am", "").replace("pm", "").strip()
    if ":" in clean_time:
        parts = clean_time.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
    else:
        hour = int(clean_time)
        minute = 0
        
    if is_pm and hour < 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0
        
    return hour, minute

def calculate_next_datetime(hour, minute):
    """Calculates the next occurrence of the given hour and minute in local time."""
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    target += timedelta(seconds=30)
    return target

def send_message_sequence(agent_name, commands):
    """Sends a sequence of commands to the agent with a small delay between each."""
    for i, command in enumerate(commands):
        log(f"Sending step {i+1}/{len(commands)} to {agent_name}: '{command}'")
        try:
            cmd = ["maestri", "ask", agent_name, command]
            subprocess.Popen(cmd)
            time.sleep(3)
        except Exception as e:
            log(f"Error sending step '{command}' to {agent_name}: {e}")

def execute_custom_task(task):
    """Executes a custom task in parallel threads for each targeted agent."""
    agents = task["agents"]
    commands_dict = task["commands"]
    log(f"Executing scheduled task ID {task['id']} for agents: {', '.join(agents)}", print_to_console=True)
    notify_os(f"Executando tarefa agendada ID {task['id']} nos terminais: {', '.join(agents)}")
    
    for agent in agents:
        agent_commands = commands_dict.get(agent, [])
        if agent_commands:
            t = threading.Thread(target=send_message_sequence, args=(agent, agent_commands))
            t.daemon = True
            t.start()

def load_tasks():
    """Loads custom tasks from persistent JSON file."""
    global state
    if not os.path.exists(TASKS_FILE):
        return
    try:
        with open(TASKS_FILE, "r") as f:
            data = json.load(f)
            
        loaded_tasks = []
        now = datetime.now()
        max_id = 0
        
        for t_data in data:
            task_id = t_data["id"]
            if task_id > max_id:
                max_id = task_id
                
            agents = t_data["agents"]
            commands = t_data["commands"]
            
            if isinstance(commands, list):
                commands = {agent: commands for agent in agents}
                
            recurring = t_data.get("recurring", False)
            
            if recurring:
                recur_time_str = t_data["recur_time"]
                hour, minute = parse_reset_time(recur_time_str)
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target_time <= now:
                    target_time += timedelta(days=1)
                
                loaded_tasks.append({
                    "id": task_id,
                    "agents": agents,
                    "commands": commands,
                    "time": target_time,
                    "recurring": True,
                    "recur_time": recur_time_str
                })
            else:
                time_str = t_data["time"]
                task_time = datetime.fromisoformat(time_str)
                if task_time > now:
                    loaded_tasks.append({
                        "id": task_id,
                        "agents": agents,
                        "commands": commands,
                        "time": task_time,
                        "recurring": False
                    })
                else:
                    log(f"Cleaning up expired one-time task ID {task_id} on startup (was scheduled for {time_str})")
                    
        with state_lock:
            state["custom_tasks"] = loaded_tasks
            state["task_counter"] = max_id + 1
            
        log(f"Successfully loaded {len(loaded_tasks)} tasks from tasks.json")
    except Exception as e:
        log(f"Error loading tasks from tasks.json: {e}")

def save_tasks():
    """Saves custom tasks to persistent JSON file."""
    with state_lock:
        tasks_to_save = []
        for task in state["custom_tasks"]:
            t_data = {
                "id": task["id"],
                "agents": task["agents"],
                "commands": task["commands"],
                "recurring": task["recurring"]
            }
            if task["recurring"]:
                t_data["recur_time"] = task["recur_time"]
            t_data["time"] = task["time"].isoformat()
            tasks_to_save.append(t_data)
            
    try:
        os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
        with open(TASKS_FILE, "w") as f:
            json.dump(tasks_to_save, f, indent=4)
        log("Tasks successfully saved to tasks.json")
    except Exception as e:
        log(f"Error saving tasks to tasks.json: {e}")

def process_signals():
    """Reads unprocessed workflow signals and triggers target actions."""
    if not os.path.exists(SIGNALS_FILE):
        return
        
    try:
        with open(SIGNALS_FILE, "r") as f:
            signals = json.load(f)
            
        unprocessed = [s for s in signals if not s.get("processed", False)]
        if not unprocessed:
            return
            
        changed = False
        for s in unprocessed:
            agent = s["agent"]
            status = s["status"]
            
            log(f"Processando sinal '{status}' recebido de '{agent}'", print_to_console=True)
            s["processed"] = True
            changed = True
            
            # Workflow Logic
            if agent == ARCHITECT_AGENT:
                if status == "aprovado":
                    log(f"Arquiteto aprovou a tarefa. Limpando contexto do operário '{WORKER_AGENT}'.", print_to_console=True)
                    notify_os(f"Spec APROVADA pelo Claude. Limpando {WORKER_AGENT}.")
                    # Run /clear on Worker terminal
                    threading.Thread(target=send_message_sequence, args=(WORKER_AGENT, ["/clear"])).start()
                elif status == "reprovado":
                    log(f"Arquiteto reprovou a tarefa. Mantendo contexto do operário '{WORKER_AGENT}' para ajustes.", print_to_console=True)
                    notify_os(f"Spec REPROVADA pelo Claude. {WORKER_AGENT} deve ajustar.")
            elif agent == WORKER_AGENT:
                if status == "concluido":
                    log(f"Operário concluiu a implementação. Aguardando validação do arquiteto '{ARCHITECT_AGENT}'.", print_to_console=True)
                    notify_os(f"Tarefa concluída pelo Codex. Aguardando validação.")
                    
        if changed:
            with open(SIGNALS_FILE, "w") as f:
                json.dump(signals, f, indent=4)
            threading.Thread(target=update_canvas_note).start()
            
    except Exception as e:
        log(f"Error in process_signals: {e}")

def background_loop():
    """Runs the periodic monitoring loop (every 15s) and checks schedules."""
    global state
    while state["running"]:
        try:
            now = datetime.now()
            
            # 1. Process signals from signals.json
            process_signals()
            
            # 2. Handle Automatic Rate Limit Monitoring (if enabled)
            with state_lock:
                monitor_enabled = state["auto_monitor_enabled"]
                
            if monitor_enabled:
                agents = get_connected_agents()
                for agent in agents:
                    if agent.lower() == "shell":
                        continue
                        
                    limit_info = check_agent_limit(agent)
                    if limit_info:
                        time_str, tz_str = limit_info
                        try:
                            hour, minute = parse_reset_time(time_str)
                            target_dt = calculate_next_datetime(hour, minute)
                            
                            with state_lock:
                                already_scheduled = False
                                if agent in state["scheduled_resets"]:
                                    for prev_target in state["scheduled_resets"][agent]:
                                        if abs((prev_target - target_dt).total_seconds()) < 3600:
                                            already_scheduled = True
                                            break
                                            
                                if not already_scheduled:
                                    log(f"Detected limit for {agent}: resets at {time_str} ({tz_str})")
                                    log(f"Scheduling wake-up message for {agent} at {target_dt.strftime('%Y-%m-%d %H:%M:%S')}", print_to_console=True)
                                    notify_os(f"Limite detectado no terminal '{agent}'. Retorno agendado para {target_dt.strftime('%H:%M:%S')}.")
                                    if agent not in state["scheduled_resets"]:
                                        state["scheduled_resets"][agent] = []
                                    state["scheduled_resets"][agent].append(target_dt)
                        except Exception as pe:
                            log(f"Failed to parse/schedule reset for {agent} ({time_str}): {pe}")
                    else:
                        with state_lock:
                            if agent in state["scheduled_resets"]:
                                state["scheduled_resets"][agent] = [t for t in state["scheduled_resets"][agent] if t > now - timedelta(hours=2)]

            # 3. Check and trigger Automatic Rate Limit wake-ups
            with state_lock:
                for agent, targets in list(state["scheduled_resets"].items()):
                    for target_dt in list(targets):
                        if now >= target_dt:
                            log(f"Auto-waking {agent} after rate-limit reset.", print_to_console=True)
                            notify_os(f"Enviando 'pode continuar' para o terminal '{agent}'.")
                            threading.Thread(target=send_message_sequence, args=(agent, ["pode continuar"])).start()
                            targets.remove(target_dt)

            # 4. Check and trigger Custom Tasks
            with state_lock:
                pending_tasks = []
                tasks_changed = False
                for task in state["custom_tasks"]:
                    if now >= task["time"]:
                        execute_custom_task(task)
                        if task["recurring"]:
                            next_time = task["time"] + timedelta(days=1)
                            while next_time <= now:
                                next_time += timedelta(days=1)
                            task["time"] = next_time
                            pending_tasks.append(task)
                            log(f"Rescheduled recurring task ID {task['id']} for {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        else:
                            log(f"One-time task ID {task['id']} completed and removed.")
                        tasks_changed = True
                    else:
                        pending_tasks.append(task)
                
                if tasks_changed:
                    state["custom_tasks"] = pending_tasks
                    save_tasks()
                    
            # 5. Periodically update canvas note
            threading.Thread(target=update_canvas_note).start()

        except Exception as e:
            log(f"Error in background loop: {e}")
            
        time.sleep(15)

def parse_relative_time(dur_str):
    """Parses relative time strings like '5m', '1h', '30s' and returns timedelta."""
    dur_str = dur_str.strip().lower()
    match = re.match(r"^(\d+)(s|m|h|d)$", dur_str)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == 's':
        return timedelta(seconds=amount)
    elif unit == 'm':
        return timedelta(minutes=amount)
    elif unit == 'h':
        return timedelta(hours=amount)
    elif unit == 'd':
        return timedelta(days=amount)
    return None

def handle_signal_cli():
    """Handles terminal command 'python3 monitor.py signal <status>' sent by agents."""
    if len(sys.argv) < 3:
        print("Erro: Status ausente. Uso: python3 monitor.py signal <concluido|aprovado|reprovado>")
        sys.exit(1)
        
    status = sys.argv[2].lower().strip()
    agent_name = os.environ.get("MAESTRI_TERMINAL_NAME")
    if not agent_name:
        print("Erro: A variável de ambiente MAESTRI_TERMINAL_NAME não está definida.")
        sys.exit(1)
        
    if status not in ["concluido", "aprovado", "reprovado"]:
        print("Erro: Status inválido. Escolha entre: concluido, aprovado, reprovado")
        sys.exit(1)
        
    try:
        signals = []
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, "r") as f:
                signals = json.load(f)
                
        signals.append({
            "agent": agent_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "processed": False
        })
        
        os.makedirs(os.path.dirname(SIGNALS_FILE), exist_ok=True)
        with open(SIGNALS_FILE, "w") as f:
            json.dump(signals, f, indent=4)
            
        print(f"✓ Sinal '{status}' registrado com sucesso para o terminal '{agent_name}'.")
    except Exception as e:
        print(f"Erro ao registrar sinal: {e}")
        sys.exit(1)

def interactive_menu():
    global state
    print("=" * 60)
    print("          MAESTRI INTERACTIVE MONITOR & SCHEDULER")
    print("=" * 60)
    print("Comandos disponíveis:")
    print("  status       - Exibe o estado do monitoramento e agendamentos")
    print("  toggle       - Ativa/Desativa o monitoramento automático de limite")
    print("  schedule     - Menu interativo para criar agendamento personalizado")
    print("  cancel       - Cancela um agendamento personalizado por ID")
    print("  create-note  - Cria uma nota de status acoplada no canvas")
    print("  logs [n]     - Imprime os últimos N registros de log (padrão: 15)")
    print("  help         - Mostra esta ajuda")
    print("  exit         - Finaliza o script")
    print("-" * 60)
    
    while state["running"]:
        try:
            cmd_input = input("maestri-monitor> ").strip()
            if not cmd_input:
                continue
                
            cmd = cmd_input.lower()
            if cmd == "exit":
                print("Encerrando monitor...")
                state["running"] = False
                break
            elif cmd == "help":
                print("Comandos: status, toggle, schedule, cancel, create-note, logs [n], help, exit")
            elif cmd == "toggle":
                with state_lock:
                    state["auto_monitor_enabled"] = not state["auto_monitor_enabled"]
                    status = "ATIVADO" if state["auto_monitor_enabled"] else "DESATIVADO"
                print(f"Monitoramento automático de limite: {status}")
                log(f"Auto monitoring toggled to: {status}")
                threading.Thread(target=update_canvas_note).start()
            elif cmd.startswith("logs"):
                parts = cmd_input.split()
                n_lines = 15
                if len(parts) > 1:
                    try:
                        n_lines = int(parts[1])
                    except ValueError:
                        print("Número de linhas inválido. Mostrando 15 linhas.")
                
                log_file = "/Users/caioamaraldepieri/maestri-monitor/monitor.log"
                if not os.path.exists(log_file):
                    print("Nenhum log encontrado ainda.")
                    continue
                    
                try:
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                    print("-" * 50)
                    print(f"Últimos {n_lines} registros de log:")
                    for line in lines[-n_lines:]:
                        print(line.strip())
                    print("-" * 50)
                except Exception as e:
                    print(f"Erro ao ler arquivo de log: {e}")
            elif cmd == "create-note":
                print("Criando nota de status no canvas...")
                try:
                    cmd_create = ["maestri", "note", "create", "# Status do Monitor Maestri\nIniciando..."]
                    subprocess.run(cmd_create, capture_output=True, text=True, check=True)
                    print("✓ Nota criada com sucesso!")
                    log("Created status note on canvas.")
                    threading.Thread(target=update_canvas_note).start()
                except Exception as e:
                    print(f"Erro ao criar nota: {e}")
            elif cmd == "status":
                print("-" * 50)
                with state_lock:
                    print(f"Monitoramento automático: {'ATIVADO' if state['auto_monitor_enabled'] else 'DESATIVADO'}")
                    
                    print("\nAgendamentos automáticos ativos:")
                    has_auto = False
                    for agent, targets in state["scheduled_resets"].items():
                        for t in targets:
                            print(f"  - {agent}: acorda em {t.strftime('%Y-%m-%d %H:%M:%S')}")
                            has_auto = True
                    if not has_auto:
                        print("  Nenhum.")
                        
                    print("\nAgendamentos personalizados ativos:")
                    if not state["custom_tasks"]:
                        print("  Nenhum.")
                    for task in state["custom_tasks"]:
                        rec_str = " (Diário)" if task["recurring"] else " (Único)"
                        print(f"  [ID {task['id']}]{rec_str} Agentes: {', '.join(task['agents'])}")
                        print(f"          Executa em: {task['time'].strftime('%Y-%m-%d %H:%M:%S')}")
                        for agent in task["agents"]:
                            cmds = task["commands"].get(agent, [])
                            print(f"          Passos para {agent}: { ' -> '.join(cmds) }")
                print("-" * 50)
            elif cmd == "schedule":
                # 1. Get connected agents
                agents = get_connected_agents()
                agents = [a for a in agents if a.lower() != "shell"]
                if not agents:
                    print("Erro: Nenhum agente conectado encontrado.")
                    continue
                
                print("\nTerminais disponíveis:")
                for idx, agent in enumerate(agents):
                    print(f"  {idx + 1}. {agent}")
                    
                selected_input = input("Escolha os terminais (números separados por vírgula, ex: 1,2): ").strip()
                selected_idxs = []
                try:
                    selected_idxs = [int(x.strip()) - 1 for x in selected_input.split(",") if x.strip()]
                except ValueError:
                    print("Seleção inválida.")
                    continue
                    
                target_agents = []
                for idx in selected_idxs:
                    if 0 <= idx < len(agents):
                        target_agents.append(agents[idx])
                        
                if not target_agents:
                    print("Nenhum terminal válido selecionado.")
                    continue
                    
                print(f"Terminais selecionados: {', '.join(target_agents)}")
                
                # 2. Command sequence wizard
                commands = {agent: [] for agent in target_agents}
                step = 1
                cancelled = False
                while True:
                    print(f"\n--- Passo {step} ---")
                    print("Escolha o tipo de ação:")
                    print("  1. Limpar terminal (/clear)")
                    print("  2. Alterar modelo (/model)")
                    print("  3. Escrever mensagem livre (qualquer prompt)")
                    print("  4. Concluir agendamento")
                    print("  5. Cancelar")
                    
                    choice = input("Ação (1-5): ").strip()
                    if choice == "1":
                        for agent in target_agents:
                            commands[agent].append("/clear")
                        print("✓ Ação '/clear' adicionada para todos os terminais.")
                    elif choice == "2":
                        # Prompt model selection for each agent
                        for agent in target_agents:
                            print(f"\nSelecione o modelo para o terminal '{agent}':")
                            if "claude" in agent.lower():
                                print("  1. Ignorar (não mudar)")
                                print("  2. sonnet (Claude 3.5 Sonnet)")
                                print("  3. haiku (Claude 3.5 Haiku)")
                                print("  4. opus (Claude 3 Opus)")
                                print("  5. high (High Effort)")
                                print("  6. low (Low Effort)")
                                print("  7. Outro (digitar manualmente)")
                                m_choice = input("Opção (1-7): ").strip()
                                if m_choice == "2":
                                    commands[agent].append("/model sonnet")
                                elif m_choice == "3":
                                    commands[agent].append("/model haiku")
                                elif m_choice == "4":
                                    commands[agent].append("/model opus")
                                elif m_choice == "5":
                                    commands[agent].append("/model high")
                                elif m_choice == "6":
                                    commands[agent].append("/model low")
                                elif m_choice == "7":
                                    custom_m = input("Digite o nome/comando do modelo: ").strip()
                                    if custom_m:
                                        commands[agent].append(f"/model {custom_m}")
                            else:
                                print("  1. Ignorar (não mudar)")
                                print("  2. gpt-4o")
                                print("  3. o1")
                                print("  4. o3-mini")
                                print("  5. gpt-5.5 medium")
                                print("  6. Outro (digitar manualmente)")
                                m_choice = input("Opção (1-6): ").strip()
                                if m_choice == "2":
                                    commands[agent].append("/model gpt-4o")
                                elif m_choice == "3":
                                    commands[agent].append("/model o1")
                                elif m_choice == "4":
                                    commands[agent].append("/model o3-mini")
                                elif m_choice == "5":
                                    commands[agent].append("/model gpt-5.5 medium")
                                elif m_choice == "6":
                                    custom_m = input("Digite o nome/comando do modelo: ").strip()
                                    if custom_m:
                                        commands[agent].append(f"/model {custom_m}")
                        print("✓ Ações de alteração de modelo salvas.")
                    elif choice == "3":
                        msg = input("Digite a mensagem livre: ").strip()
                        if msg:
                            for agent in target_agents:
                                commands[agent].append(msg)
                            print("✓ Mensagem adicionada para todos os terminais.")
                    elif choice == "4":
                        has_commands = False
                        for agent in target_agents:
                            if commands[agent]:
                                has_commands = True
                                break
                        if not has_commands:
                            print("Nenhum comando adicionado na sequência. Adicione ao menos um passo.")
                            continue
                        break
                    elif choice == "5":
                        cancelled = True
                        break
                    else:
                        print("Opção inválida.")
                        continue
                    
                    step += 1
                    
                if cancelled:
                    print("Cancelado.")
                    continue
                    
                # 3. Recurring or One-time
                is_recurring = False
                recur_time = ""
                rep_input = input("\nEsta tarefa deve se repetir diariamente? (s/n): ").strip().lower()
                
                if rep_input == "s" or rep_input == "sim":
                    is_recurring = True
                    recur_time = input("Digite o horário de repetição diária (HH:MM): ").strip()
                    try:
                        hour, minute = parse_reset_time(recur_time)
                        now = datetime.now()
                        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if target_time <= now:
                            target_time += timedelta(days=1)
                    except Exception:
                        print("Horário de repetição inválido. Cancelado.")
                        continue
                else:
                    # One-time schedule input
                    print("\nQuando executar?")
                    print("Formatos aceitos:")
                    print("  - Tempo relativo: ex: 5m, 1h, 30s")
                    print("  - Horário específico hoje/amanhã: ex: 23:30")
                    print("  - Data e hora completas: ex: 2026-07-03 23:30")
                    time_input = input("Quando: ").strip()
                    
                    target_time = None
                    rel_delta = parse_relative_time(time_input)
                    if rel_delta:
                        target_time = datetime.now() + rel_delta
                    else:
                        try:
                            t_parts = datetime.strptime(time_input, "%H:%M")
                            now = datetime.now()
                            target_time = now.replace(hour=t_parts.hour, minute=t_parts.minute, second=0, microsecond=0)
                            if target_time <= now:
                                target_time += timedelta(days=1)
                        except ValueError:
                            try:
                                target_time = datetime.strptime(time_input, "%Y-%m-%d %H:%M")
                            except ValueError:
                                pass
                                
                    if not target_time:
                        print("Formato de data/hora inválido. Cancelado.")
                        continue
                
                # Save task
                with state_lock:
                    task_id = state["task_counter"]
                    state["task_counter"] += 1
                    new_task = {
                        "id": task_id,
                        "agents": target_agents,
                        "commands": commands,
                        "time": target_time,
                        "recurring": is_recurring,
                        "recur_time": recur_time
                    }
                    state["custom_tasks"].append(new_task)
                    save_tasks()
                    
                rec_label = "Diário" if is_recurring else "Único"
                print(f"✓ Agendamento ({rec_label}) criado com sucesso!")
                print(f"  [ID {task_id}] Executará em {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
                log(f"Custom task {task_id} ({rec_label}) scheduled for {', '.join(target_agents)} at {target_time}")
                threading.Thread(target=update_canvas_note).start()
            elif cmd == "cancel":
                try:
                    task_id_to_cancel = int(input("Digite o ID do agendamento para cancelar: ").strip())
                except ValueError:
                    print("ID inválido.")
                    continue
                    
                found = False
                with state_lock:
                    filtered_tasks = []
                    for task in state["custom_tasks"]:
                        if task["id"] == task_id_to_cancel:
                            found = True
                            log(f"Custom task {task_id_to_cancel} cancelled by user.")
                        else:
                            filtered_tasks.append(task)
                    state["custom_tasks"] = filtered_tasks
                    if found:
                        save_tasks()
                    
                if found:
                    print(f"✓ Agendamento ID {task_id_to_cancel} cancelado.")
                    threading.Thread(target=update_canvas_note).start()
                else:
                    print("Agendamento não encontrado.")
            else:
                print("Comando desconhecido. Digite 'help' para ver os comandos.")
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando monitor...")
            state["running"] = False
            break

if __name__ == "__main__":
    # Check if we are running in signal CLI mode
    if len(sys.argv) > 1 and sys.argv[1] == "signal":
        handle_signal_cli()
    else:
        # Load any tasks from disk
        load_tasks()
        
        # Start the monitoring thread
        t = threading.Thread(target=background_loop)
        t.daemon = True
        t.start()
        
        # Start interactive menu in main thread
        interactive_menu()

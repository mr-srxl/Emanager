import os
import re
import shlex
import sys
import shutil

class COLORS:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m' 


HOSTS_FILE_PATH = '/etc/hosts' 
NOTES_FILE_PATH = os.path.expanduser('~/manager_notes.txt') 

HOSTS_ALIAS_CONCEPTUAL = "/etc/hosts"
NOTES_ALIAS_CONCEPTUAL = "~/manager_notes.txt"


try:
    import readline
except ImportError:
    def command_completer(text, state): return None
    def setup_autocomplete(): pass
    AVAILABLE_COMMANDS = []
else:
    
    AVAILABLE_COMMANDS = ['export', 'print', 'del', 'quit', 'exit', 'clear', 'add', 'commit', 'note']
    
    def command_completer(text, state):
        """Custom completer for interactive commands."""
        if text.startswith('add '):
            parts = text.split(' ', 2)
            if len(parts) == 2:
                add_options = ['host', 'note']
                options = [f"add {opt} " for opt in add_options if opt.startswith(parts[1])]
            else:
                options = [] 
        elif text.startswith('print '):
            parts = text.split(' ', 2)
            if len(parts) == 2:
                print_options = ['notes']
                options = [f"print {opt}" for opt in print_options if opt.startswith(parts[1])]
            else:
                options = [] 
        else:
            options = [cmd for cmd in AVAILABLE_COMMANDS if cmd.startswith(text)]
            options = [opt + " " if opt in ['export', 'del', 'add', 'print'] else opt for opt in options] 
        
        if state < len(options):
            return options[state]
        else:
            return None

    def setup_autocomplete():
        """Sets up readline for tab completion."""
        try:
            readline.set_completer_delims(' \t\n')
            readline.set_completer(command_completer)
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass 


EXPORT_START = "#Start_of_export_manager_block"
EXPORT_END = "#End_of_export_manager_block"
HOSTS_START = "#Start_of_hosts_manager_block"
HOSTS_END = "#End_of_hosts_manager_block"
NOTES_START = "#Start_of_notes_manager_block"
NOTES_END = "#End_of_notes_manager_block"


def check_write_permission(file_path, alias):
    """Checks if the user has write permission to the file path. (Permission handling kept for robustness)"""
    if os.path.exists(file_path):
        if not os.access(file_path, os.W_OK):
            print(f"{COLORS.RED}🚨 PERMISSION DENIED: You cannot write to {COLORS.CYAN}{alias}{COLORS.RED} at {file_path}.{COLORS.END}")
            print(f"{COLORS.YELLOW}Please run this script with {COLORS.CYAN}{COLORS.BOLD}sudo{COLORS.END}{COLORS.YELLOW} if you intend to modify system files.{COLORS.END}")
            return False
    else:
        
        dir_path = os.path.dirname(file_path) or '.'
        if not os.access(dir_path, os.W_OK):
            print(f"{COLORS.RED}🚨 PERMISSION DENIED: Cannot create file in directory {dir_path}.{COLORS.END}")
            print(f"{COLORS.YELLOW}Please run this script with {COLORS.CYAN}{COLORS.BOLD}sudo{COLORS.END}{COLORS.YELLOW} if you intend to create system files.{COLORS.END}")
            return False
    return True

def delete_all_in_block(file_path, start_marker, end_marker, alias):
    """Deletes all content between the start and end markers, preserving the markers."""
    if not check_write_permission(file_path, alias):
        return False
        
    lines = []
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"{COLORS.RED}File {alias} not found at {file_path}.{COLORS.END}")
        return False
        
    updated_lines = []
    in_block = False
    lines_deleted_count = 0
    
    for line in lines:
        clean_line = line.strip()
        
        if clean_line == start_marker:
            in_block = True
            updated_lines.append(line)
            continue
        
        if clean_line == end_marker:
            in_block = False
            updated_lines.append(line) 
            continue
            
        if in_block:
            lines_deleted_count += 1
            continue 
            
        updated_lines.append(line) 

    try:
        with open(file_path, 'w') as f:
            f.writelines(updated_lines)
            
        print(f"{COLORS.GREEN}✅ Deleted {lines_deleted_count} entries from {COLORS.CYAN}{alias}{COLORS.GREEN} block.{COLORS.END}")
        return True
    except Exception as e:
        print(f"{COLORS.RED}Error writing to file {alias} at {file_path}: {e}{COLORS.END}")
        return False

def sync_file_block(file_path, start_marker, end_marker, alias):
    if not check_write_permission(file_path, alias):
        return (-1, -1)
        
    start_index = -1
    end_index = -1
    lines = []
    file_exists = os.path.exists(file_path)
    
    if file_exists:
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines() 
        except Exception as e:
            print(f"{COLORS.RED}CRITICAL READ ERROR for {alias}: {e}{COLORS.END}")
            return (-1, -1)
    else:
        print(f"{COLORS.YELLOW}⚠️ File {COLORS.CYAN}{alias}{COLORS.YELLOW} not found at {file_path}. Creating and initializing with empty block.{COLORS.END}")
        
        lines = [f"{start_marker}\n", f"{end_marker}\n"] 
        start_index = 1 
        end_index = 2   
        
        try:
            with open(file_path, 'w') as f:
                f.writelines(lines)
        except Exception as e:
            print(f"{COLORS.RED}CRITICAL ERROR: Could not create file at {file_path}. Check permissions. ({e}){COLORS.END}")
            return (-1, -1)
            
        return (start_index, end_index)
            
    
    start_found = False
    end_found = False
    new_lines_needed = False
    
    for line_number, line in enumerate(lines, 1):
        clean_line = line.strip()
        if clean_line == start_marker:
            start_found = True
            start_index = line_number
        elif clean_line == end_marker:
            end_found = True
            end_index = line_number

    if not start_found or not end_found:
        if not start_found:
            lines.append(f"\n{start_marker}\n")
            start_index = len(lines)
            new_lines_needed = True
        if not end_found:
            lines.append(f"{end_marker}\n")
            end_index = len(lines)
            new_lines_needed = True
        
    if new_lines_needed or not file_exists: 
         try:
             with open(file_path, 'w') as f:
                f.writelines(lines)
         except Exception as e:
             print(f"{COLORS.RED}CRITICAL WRITE ERROR for {alias}: Could not write to file at {file_path}. Check permissions. ({e}){COLORS.END}")
             return (-1, -1)
            
    return (start_index, end_index)

def get_entries_in_block(file_path, start_index, end_index, pattern_type='export'):
    """Retrieves entries within the specified block."""
    if pattern_type == 'export':
        entry_pattern = re.compile(r"export\s+[a-zA-Z_][a-zA-Z0-9_]*=.*")
    elif pattern_type == 'host':
        entry_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+.*")
    elif pattern_type == 'note':
        entry_pattern = re.compile(r"NOTE:.*")
    else:
        return []
        
    entries = []
    
    try:
        with open(file_path, 'r') as f:
            for line_number, line in enumerate(f, 1):
                # Only look between the markers
                if line_number > start_index and line_number < end_index:
                    clean_line = line.strip()
                    if entry_pattern.match(clean_line):
                        entries.append((line_number, clean_line, file_path))
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"{COLORS.RED}Error reading entries from {file_path}: {e}{COLORS.END}", file=sys.stderr)
        return []
        
    return entries

def delete_entry_line(file_path, line_to_delete, alias):
    """Deletes a specific line by its 1-based number, operating on the persistent file."""
    if not check_write_permission(file_path, alias):
        return False, "Permission denied."
        
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        delete_index = line_to_delete - 1
        
        if 0 <= delete_index < len(lines):
            deleted_line = lines.pop(delete_index)
            
            # qrite the file back without the deleted line.
            with open(file_path, 'w') as f:
                f.writelines(lines)
                
            return True, deleted_line.strip()
        else:
            return False, "Line number out of range."

    except Exception as e:
        return False, f"Exception occurred during file deletion: {e}"

def insert_host_entry(file_path, ip_address, domain_name, sub_domain, end_index, start_index, alias):
    """Inserts or updates a host entry in the hosts block by reading, modifying, and overwriting the persistent file."""
    if not check_write_permission(file_path, alias):
        return end_index
        
    hosts_entry = f"{ip_address}\t{domain_name} {sub_domain}".strip()
    new_line = hosts_entry + "\n"
    
    with open(file_path, 'r') as f:
        file_lines = f.readlines()
        
    updated_lines = []
    lines_deleted_count = 0
    
    start_marker_index_0 = start_index - 1
    end_marker_index_0 = end_index - 1
    

    hosts_entry_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+.*?\b" + re.escape(domain_name) + r"\b.*")
    

    for i, line in enumerate(file_lines):
        if i > start_marker_index_0 and i < end_marker_index_0:
            if hosts_entry_pattern.match(line.strip()):
                lines_deleted_count += 1
                continue 
        
        updated_lines.append(line)

    end_marker_content = HOSTS_END
    
    new_end_index_0 = next((i for i, line in enumerate(updated_lines) if line.strip() == end_marker_content), -1)

    if new_end_index_0 == -1:
        print(f"{COLORS.RED}CRITICAL ERROR: Hosts End marker disappeared during line processing.{COLORS.END}")
        return end_index 

    updated_lines.insert(new_end_index_0, new_line)
    
    try:
        with open(file_path, 'w') as f: 
            f.writelines(updated_lines)
    except Exception as e:
        print(f"{COLORS.RED}Error writing host entry to file: {e}{COLORS.END}")
        return end_index
        
    if lines_deleted_count > 0:
        print(f"{COLORS.GREEN}✅ {COLORS.BOLD}Replaced/Updated{COLORS.END}{COLORS.GREEN} host entry for '{domain_name}'. Deleted {lines_deleted_count} old instance(s).{COLORS.END}")
    else:
        print(f"{COLORS.GREEN}✅ {COLORS.BOLD}Inserted{COLORS.END}{COLORS.GREEN} new host entry: '{hosts_entry}'{COLORS.END}")

    return new_end_index_0 + 2

def insert_export_command(file_path, command, end_index, start_index, alias):
    """Inserts or updates an export command, overwriting the persistent file."""
    if not check_write_permission(file_path, alias):
        return end_index
        
    export_name_pattern = re.compile(r"export\s+([a-zA-Z_][a-zA-Z0-9_]*)=.*")
    
    with open(file_path, 'r') as f:
        file_lines = f.readlines()
        
    new_line = command.strip() + "\n"
    new_match = export_name_pattern.match(command.strip())
    
    if not new_match:
        print(f"{COLORS.RED}Error: Could not parse variable name from command.{COLORS.END}")
        return end_index 
        
    new_var_name = new_match.group(1)
    
    updated_lines = []
    lines_deleted_count = 0
    
    start_marker_index_0 = start_index - 1
    end_marker_index_0 = end_index - 1
    
  
    for i, line in enumerate(file_lines):
        if i > start_marker_index_0 and i < end_marker_index_0:
            existing_match = export_name_pattern.match(line.strip())
            
            if existing_match and existing_match.group(1) == new_var_name:
                lines_deleted_count += 1
                continue 
        
        
        updated_lines.append(line)


    end_marker_content = EXPORT_END
    new_end_index_0 = next((i for i, line in enumerate(updated_lines) if line.strip() == end_marker_content), -1)
    
    if new_end_index_0 == -1:
        print(f"{COLORS.RED}CRITICAL ERROR: End marker disappeared during line processing.{COLORS.END}")
        return end_index 

    updated_lines.insert(new_end_index_0, new_line)
    
    try:
        with open(file_path, 'w') as f: 
            f.writelines(updated_lines)
    except Exception as e:
        print(f"{COLORS.RED}Error writing export command to file: {e}{COLORS.END}")
        return end_index

    if lines_deleted_count > 0:
        print(f"{COLORS.GREEN}✅ {COLORS.BOLD}Replaced/Updated{COLORS.END}{COLORS.GREEN} variable '{new_var_name}'. Deleted {lines_deleted_count} old instance(s).{COLORS.END}")
    else:
        print(f"{COLORS.GREEN}✅ {COLORS.BOLD}Inserted{COLORS.END}{COLORS.GREEN} new command: '{command.strip()}'{COLORS.END}")

    return new_end_index_0 + 2 
    
def insert_note_entry(file_path, note_content, end_index, alias):
    """Inserts a new note entry, appending it before the end marker, and updates the file immediately."""
    if not check_write_permission(file_path, alias):
        return end_index
        
    new_line = f"NOTE: {note_content.strip()}\n"
    
    try:
        with open(file_path, 'r') as f:
            file_lines = f.readlines()
            
        end_marker_index_0 = end_index - 1
        
        if end_marker_index_0 < 0 or end_marker_index_0 >= len(file_lines):
            print(f"{COLORS.RED}CRITICAL ERROR: Notes End marker index is invalid.{COLORS.END}")
            return end_index

      
        updated_lines = file_lines
        updated_lines.insert(end_marker_index_0, new_line)
        
        with open(file_path, 'w') as f: 
            f.writelines(updated_lines)
            
        print(f"{COLORS.GREEN}✅ {COLORS.BOLD}Inserted{COLORS.END}{COLORS.GREEN} new note to {COLORS.CYAN}{alias}{COLORS.GREEN}.{COLORS.END}")
        return end_index + 1 
        
    except Exception as e:
        print(f"{COLORS.RED}Error inserting note: {e}{COLORS.END}")
        return end_index



def main():
    """Main function to run the interactive loop."""

   
    current_shell_path = os.environ.get('SHELL')
    
    if not current_shell_path:
        print(f"{COLORS.RED}🚨 ERROR: Could not determine current shell ($SHELL environment variable is missing).{COLORS.END}")
        return

    shell_name = os.path.basename(current_shell_path).lower()
    
    if 'bash' in shell_name:
        shell_file_path = os.path.expanduser('~/.bashrc')
        shell_alias_conceptual = "~/.bashrc"
        shell = "bash"
    elif 'zsh' in shell_name:
        shell_file_path = os.path.expanduser('~/.zshrc')
        shell_alias_conceptual = "~/.zshrc"
        shell = "zsh"
    else:
        print(f"{COLORS.RED}🚨 UNSUPPORTED SHELL: Detected shell is '{shell_name}'.{COLORS.END}")
        print(f"{COLORS.YELLOW}This manager only supports {COLORS.BOLD}bash{COLORS.END}{COLORS.YELLOW} (using ~/.bashrc) and {COLORS.BOLD}zsh{COLORS.END}{COLORS.YELLOW} (using ~/.zshrc). Exiting.{COLORS.END}")
        return

 
    SIMULATED_USERNAME = "user" 
    
    print(f"{COLORS.BLUE}{COLORS.BOLD}\n--- Shell Configuration Manager Started ({shell.upper()} mode) ---{COLORS.END}")
    
   
    BACKUP_FILE_PATH = shell_file_path + ".manager_bak"
    
    if os.path.exists(shell_file_path) and not os.path.exists(BACKUP_FILE_PATH):
        try:
            shutil.copy2(shell_file_path, BACKUP_FILE_PATH)
            print(f"{COLORS.YELLOW}⚠️ Created one-time backup: {COLORS.CYAN}{shell_alias_conceptual}{COLORS.END}{COLORS.YELLOW} copied to {os.path.basename(BACKUP_FILE_PATH)}.{COLORS.END}")
        except Exception as e:
            print(f"{COLORS.RED}🚨 WARNING: Could not create backup at {BACKUP_FILE_PATH}. Proceeding without backup. ({e}){COLORS.END}")
    
    if not os.access(HOSTS_FILE_PATH, os.W_OK):
        print("="*60)
        print(f"{COLORS.YELLOW}⚠️  WARNING: You likely need {COLORS.CYAN}{COLORS.BOLD}sudo{COLORS.END}{COLORS.YELLOW} to modify the /etc/hosts file. ⚠️{COLORS.END}")
        print(f"{COLORS.YELLOW}If commands fail with Permission Denied, please restart with {COLORS.CYAN}`sudo python ...`{COLORS.END}")
        print("="*60)
        
    setup_autocomplete()
    
    # 1. Ensure markers exist and get the initial indices
    print(f"\nInitializing {COLORS.CYAN}{shell_alias_conceptual}{COLORS.END} at {shell_file_path}...")
    export_start_index, export_end_index = sync_file_block(shell_file_path, EXPORT_START, EXPORT_END, shell_alias_conceptual)
    
    print(f"Initializing {COLORS.CYAN}{HOSTS_ALIAS_CONCEPTUAL}{COLORS.END} at {HOSTS_FILE_PATH}...")
    hosts_start_index, hosts_end_index = sync_file_block(HOSTS_FILE_PATH, HOSTS_START, HOSTS_END, HOSTS_ALIAS_CONCEPTUAL)
    
    print(f"Initializing {COLORS.CYAN}{NOTES_ALIAS_CONCEPTUAL}{COLORS.END} at {NOTES_FILE_PATH}...")
    notes_start_index, notes_end_index = sync_file_block(NOTES_FILE_PATH, NOTES_START, NOTES_END, NOTES_ALIAS_CONCEPTUAL)

    
    if export_start_index == -1 or hosts_start_index == -1 or notes_start_index == -1:
        print(f"{COLORS.RED}Initialization failed due to critical error or permissions. Exiting.{COLORS.END}")
        return
    
    print(f"\n{COLORS.BOLD}--- Command Reference ---{COLORS.END}")
    print(f"Export Variable: {COLORS.CYAN}{COLORS.BOLD}export NAME=VALUE{COLORS.END} (e.g., `export PROJECT_PATH=/data/web`)")
    print(f"Add Host Entry: {COLORS.CYAN}{COLORS.BOLD}add host <ip> <domain> [subdomain]{COLORS.END} (e.g., `add host 192.168.1.1 mysite.local`)")
    print(f"Add Note: {COLORS.CYAN}{COLORS.BOLD}add note <text>{COLORS.END} (Saves instantly to file)")
    print(f"Apply Changes: {COLORS.CYAN}{COLORS.BOLD}commit{COLORS.END} (Required for exports and hosts, but not for notes)")
    print(f"List Entries: {COLORS.CYAN}{COLORS.BOLD}print{COLORS.END} | {COLORS.CYAN}{COLORS.BOLD}print notes{COLORS.END} | Delete Entry: {COLORS.CYAN}{COLORS.BOLD}del <number>{COLORS.END}")
    print(f"Bulk Delete: {COLORS.CYAN}{COLORS.BOLD}del all{COLORS.END} (exports) | {COLORS.CYAN}{COLORS.BOLD}del host all{COLORS.END} (hosts)")

    export_pattern = re.compile(r"export\s+([a-zA-Z_][a-zA-Z0-9_]*)=(.+)")
    del_pattern = re.compile(r"del\s+(\d+)", re.IGNORECASE)
    add_host_pattern = re.compile(r"add\s+host\s+(.+)", re.IGNORECASE)
    add_note_pattern = re.compile(r"add\s+note\s+(.+)", re.IGNORECASE)
    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    domain_pattern = re.compile(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    
    del_all_exports_pattern = re.compile(r"del\s+all$", re.IGNORECASE)
    del_all_hosts_pattern = re.compile(r"del\s+host\s+all$", re.IGNORECASE)
    print_notes_pattern = re.compile(r"print\s+notes$", re.IGNORECASE)


    while True:
        try:
            command = input(f"{SIMULATED_USERNAME}@{shell} >> ").strip()
        except EOFError:
            print(f"\n{COLORS.YELLOW}Exiting program.{COLORS.END}")
            break
        
        if not command:
            continue
            
        if command.lower() in ("quit", "exit"):
            print(f"{COLORS.YELLOW}Exiting program.{COLORS.END}")
            break
        
        if command.lower() == "clear":
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Console cleared.")
            continue
            
        if command.lower() == "commit":
            
            export_start_index, export_end_index = sync_file_block(shell_file_path, EXPORT_START, EXPORT_END, shell_alias_conceptual)
            hosts_start_index, hosts_end_index = sync_file_block(HOSTS_FILE_PATH, HOSTS_START, HOSTS_END, HOSTS_ALIAS_CONCEPTUAL)
            notes_start_index, notes_end_index = sync_file_block(NOTES_FILE_PATH, NOTES_START, NOTES_END, NOTES_ALIAS_CONCEPTUAL)
            print(f"{COLORS.GREEN}✅ Configuration files written.{COLORS.END}")
            print(f"{COLORS.YELLOW}⭐ {COLORS.BOLD}ACTION REQUIRED{COLORS.END}{COLORS.YELLOW}: To load the new variables into your current shell, run: {COLORS.CYAN}{COLORS.BOLD}source {shell_file_path}{COLORS.END}")
            continue
        
        # 2. Print 
        if command.lower() == "print":
            exports = get_entries_in_block(shell_file_path, export_start_index, export_end_index, 'export')
            hosts = get_entries_in_block(HOSTS_FILE_PATH, hosts_start_index, hosts_end_index, 'host')
            notes = get_entries_in_block(NOTES_FILE_PATH, notes_start_index, notes_end_index, 'note')
            all_entries = exports + hosts + notes
            
            if not all_entries:
                print(f"\n{COLORS.YELLOW}No entries found in any managed block.{COLORS.END}")
                continue

            print(f"\n{COLORS.BOLD}--- All Managed Entries ---{COLORS.END}")
            for i, (line_num, cmd, file_path) in enumerate(all_entries, 1):
                if file_path == shell_file_path:
                    block_type = f"{COLORS.CYAN}EXP{COLORS.END}"
                    display_path = shell_alias_conceptual
                elif file_path == HOSTS_FILE_PATH:
                    block_type = f"{COLORS.BLUE}HST{COLORS.END}"
                    display_path = HOSTS_ALIAS_CONCEPTUAL
                else:
                    block_type = f"{COLORS.PURPLE}NOTE{COLORS.END}"
                    display_path = NOTES_ALIAS_CONCEPTUAL
                    
                print(f"[{COLORS.BOLD}{i}{COLORS.END}][{block_type}] ({display_path} Line {line_num}): {cmd}")
            print(f"{COLORS.BOLD}---------------------------{COLORS.END}\n")
            continue
            
        if print_notes_pattern.match(command):
            notes = get_entries_in_block(NOTES_FILE_PATH, notes_start_index, notes_end_index, 'note')
            
            if not notes:
                print(f"\n{COLORS.YELLOW}No notes found in the {NOTES_ALIAS_CONCEPTUAL} block.{COLORS.END}")
                continue

            print(f"\n{COLORS.BOLD}--- Notes from {NOTES_ALIAS_CONCEPTUAL} ---{COLORS.END}")
            for i, (line_num, cmd, file_path) in enumerate(notes, 1):
                note_content = cmd.replace("NOTE: ", "", 1)
                print(f"[{COLORS.BOLD}{i}{COLORS.END}]: {note_content}")
            print(f"{COLORS.BOLD}------------------------------{COLORS.END}\n")
            continue


        if del_all_exports_pattern.match(command):
            if delete_all_in_block(shell_file_path, EXPORT_START, EXPORT_END, shell_alias_conceptual):
                export_start_index, export_end_index = sync_file_block(shell_file_path, EXPORT_START, EXPORT_END, shell_alias_conceptual)
            continue
        
        if del_all_hosts_pattern.match(command):
            if delete_all_in_block(HOSTS_FILE_PATH, HOSTS_START, HOSTS_END, HOSTS_ALIAS_CONCEPTUAL):
                hosts_start_index, hosts_end_index = sync_file_block(HOSTS_FILE_PATH, HOSTS_START, HOSTS_END, HOSTS_ALIAS_CONCEPTUAL)
            continue

        if del_match := del_pattern.match(command):
            try:
                entry_num_to_delete = int(del_match.group(1))
                
                exports = get_entries_in_block(shell_file_path, export_start_index, export_end_index, 'export')
                hosts = get_entries_in_block(HOSTS_FILE_PATH, hosts_start_index, hosts_end_index, 'host')
                notes = get_entries_in_block(NOTES_FILE_PATH, notes_start_index, notes_end_index, 'note')
                all_entries = exports + hosts + notes
                
                if 1 <= entry_num_to_delete <= len(all_entries):
                    target_entry = all_entries[entry_num_to_delete - 1]
                    file_line_to_delete = target_entry[0]
                    file_path = target_entry[2]
                    
                    if file_path == shell_file_path:
                        display_path = shell_alias_conceptual
                    elif file_path == HOSTS_FILE_PATH:
                        display_path = HOSTS_ALIAS_CONCEPTUAL
                    else:
                        display_path = NOTES_ALIAS_CONCEPTUAL
                        
                    success, deleted_content = delete_entry_line(file_path, file_line_to_delete, display_path)
                    
                    if success:
                        
                        if file_path == shell_file_path:
                            export_start_index, export_end_index = sync_file_block(shell_file_path, EXPORT_START, EXPORT_END, shell_alias_conceptual)
                        elif file_path == HOSTS_FILE_PATH:
                            hosts_start_index, hosts_end_index = sync_file_block(HOSTS_FILE_PATH, HOSTS_START, HOSTS_END, HOSTS_ALIAS_CONCEPTUAL)
                        else:
                            notes_start_index, notes_end_index = sync_file_block(NOTES_FILE_PATH, NOTES_START, NOTES_END, NOTES_ALIAS_CONCEPTUAL)

                        print(f"{COLORS.GREEN}✅ Deleted entry [{COLORS.BOLD}{entry_num_to_delete}{COLORS.END}{COLORS.GREEN}]: '{deleted_content}' from {COLORS.CYAN}{display_path}{COLORS.END}")
                            
                    elif deleted_content != "Permission denied.":
                        print(f"{COLORS.RED}Error deleting line {file_line_to_delete}: {deleted_content}{COLORS.END}")
                        
                else:
                    print(f"{COLORS.YELLOW}Invalid entry number: [{entry_num_to_delete}]. Use 'print' to see valid numbers.{COLORS.END}")
                    
            except ValueError:
                print(f"{COLORS.YELLOW}Invalid format for 'del'. Use {COLORS.CYAN}'del <number>'{COLORS.END}{COLORS.YELLOW}.{COLORS.END}")

     
        
        elif add_note_match := add_note_pattern.match(command):
            note_content = add_note_match.group(1).strip()
            
            if not note_content:
                print(f"{COLORS.YELLOW}Invalid 'add note' format. Usage: {COLORS.CYAN}{COLORS.BOLD}add note <text>{COLORS.END}{COLORS.YELLOW}.{COLORS.END}")
                continue

            notes_end_index = insert_note_entry(
                NOTES_FILE_PATH,
                note_content,
                notes_end_index,
                NOTES_ALIAS_CONCEPTUAL
            )
        
            notes_start_index, notes_end_index = sync_file_block(NOTES_FILE_PATH, NOTES_START, NOTES_END, NOTES_ALIAS_CONCEPTUAL)
            
        elif add_match := add_host_pattern.match(command):
            try:
                args = shlex.split(add_match.group(1))
            except ValueError:
                print(f"{COLORS.RED}Error: Unclosed quotes in arguments.{COLORS.END}")
                continue

            if len(args) < 2:
                print(f"{COLORS.YELLOW}Invalid 'add host' format. Usage: {COLORS.CYAN}{COLORS.BOLD}add host <ip> <domain> [subdomain]{COLORS.END}{COLORS.YELLOW}.{COLORS.END}")
                continue
                
            ip_address = args[0]
            domain_name = args[1]
            sub_domain = " ".join(args[2:]) if len(args) > 2 else ""

            if not ip_pattern.match(ip_address):
                print(f"{COLORS.RED}Invalid IP address format: {ip_address}{COLORS.END}")
                continue
            if not domain_pattern.match(domain_name):
                print(f"{COLORS.RED}Invalid domain name format: {domain_name}{COLORS.END}")
                continue

            hosts_end_index = insert_host_entry(
                HOSTS_FILE_PATH,
                ip_address,
                domain_name,
                sub_domain,
                hosts_end_index,
                hosts_start_index,
                HOSTS_ALIAS_CONCEPTUAL
            )
            
            hosts_start_index, hosts_end_index = sync_file_block(HOSTS_FILE_PATH, HOSTS_START, HOSTS_END, HOSTS_ALIAS_CONCEPTUAL)
            print(f"{COLORS.YELLOW}NOTE: Run {COLORS.CYAN}{COLORS.BOLD}commit{COLORS.END}{COLORS.YELLOW} to finalize.{COLORS.END}")
            
        elif match := export_pattern.match(command):
            
            export_end_index = insert_export_command(
                shell_file_path, 
                command, 
                export_end_index,
                export_start_index,
                shell_alias_conceptual
            )
            
            export_start_index, export_end_index = sync_file_block(shell_file_path, EXPORT_START, EXPORT_END, shell_alias_conceptual)
            
            print(f"{COLORS.YELLOW}NOTE: Run {COLORS.CYAN}{COLORS.BOLD}commit{COLORS.END}{COLORS.YELLOW} to finalize and get the {COLORS.BOLD}source{COLORS.END}{COLORS.YELLOW} command.{COLORS.END}")
            
        else:
            print(f"{COLORS.YELLOW}Invalid command. Use {COLORS.CYAN}{COLORS.BOLD}commit{COLORS.END}{COLORS.YELLOW}, {COLORS.CYAN}{COLORS.BOLD}print{COLORS.END}{COLORS.YELLOW}, {COLORS.CYAN}{COLORS.BOLD}export NAME=VALUE{COLORS.END}{COLORS.YELLOW}, {COLORS.CYAN}{COLORS.BOLD}add host{COLORS.END}{COLORS.YELLOW}, or {COLORS.CYAN}{COLORS.BOLD}del <number>{COLORS.END}{COLORS.YELLOW}.{COLORS.END}")

if __name__ == "__main__":
    main()
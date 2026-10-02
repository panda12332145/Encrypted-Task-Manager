"""Regras de negócio das tarefas (sem I/O de terminal — testável)."""
import base64
import datetime
import os
import uuid

from .storage import decrypt, derive_key, encrypt, load_index, save_index, task_dir

MAX_NAME = 50
MAX_DESC = 500


class WrongPassword(Exception):
    """Senha mestra incorreta (ou dado corrompido)."""


def _safe_name(task_id: str, enc_name: str) -> str:
    token = base64.urlsafe_b64encode(enc_name.encode()).decode()
    return f"{task_id}_{token}.taf"


def create_task_values(password: str, name: str, desc: str) -> str:
    if not name.strip():
        raise ValueError("Nome não pode ser vazio.")
    if len(name) > MAX_NAME:
        raise ValueError(f"Nome excede {MAX_NAME} caracteres.")
    if len(desc) > MAX_DESC:
        raise ValueError(f"Descrição excede {MAX_DESC} caracteres.")

    salt = os.urandom(16)
    key = derive_key(password, salt)
    task_id = str(uuid.uuid4())

    enc_name = encrypt(key, name)
    filename = _safe_name(task_id, enc_name)
    filepath = os.path.join(task_dir(), filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(encrypt(key, desc))

    tasks = load_index()
    tasks.append({
        "id": task_id,
        "concluida": False,
        "data_criacao": datetime.datetime.now().isoformat(timespec="seconds"),
        "nome_arquivo": filename,
        "salt": base64.b64encode(salt).decode(),
    })
    save_index(tasks)
    return task_id


def list_tasks(password: str) -> list:
    """Retorna as tarefas decifradas: [{id, nome, desc, concluida, data}]."""
    out = []
    for t in load_index():
        try:
            salt = base64.b64decode(t["salt"])
            key = derive_key(password, salt)
            filepath = os.path.join(task_dir(), t["nome_arquivo"])
            with open(filepath, encoding="utf-8") as f:
                desc = decrypt(key, f.read())
            enc_name = t["nome_arquivo"].split("_", 1)[1].rsplit(".", 1)[0]
            name = decrypt(key, base64.urlsafe_b64decode(enc_name).decode())
        except Exception as e:
            raise WrongPassword(
                "Senha incorreta ou dado corrompido."
            ) from e
        out.append({
            "id": t["id"],
            "nome": name,
            "desc": desc,
            "concluida": t.get("concluida", False),
            "data_criacao": t.get("data_criacao", ""),
        })
    return out


def edit_task_values(password: str, task_id: str,
                     name: str = None, desc: str = None,
                     concluida: bool = None) -> None:
    """Edita uma tarefa existente (re-cifra com o MESMO salt/chave)."""
    tasks = load_index()
    entry = next((t for t in tasks if t["id"] == task_id), None)
    if entry is None:
        raise KeyError(f"Tarefa {task_id} não encontrada.")

    salt = base64.b64decode(entry["salt"])
    key = derive_key(password, salt)
    filepath = os.path.join(task_dir(), entry["nome_arquivo"])

    try:
        with open(filepath, encoding="utf-8") as f:
            cur_desc = decrypt(key, f.read())
        enc_name = entry["nome_arquivo"].split("_", 1)[1].rsplit(".", 1)[0]
        cur_name = decrypt(key, base64.urlsafe_b64decode(enc_name).decode())
    except Exception as e:
        raise WrongPassword("Senha incorreta ou dado corrompido.") from e

    new_name = cur_name if name is None else name
    new_desc = cur_desc if desc is None else desc
    if not new_name.strip():
        raise ValueError("Nome não pode ser vazio.")
    if len(new_name) > MAX_NAME:
        raise ValueError(f"Nome excede {MAX_NAME} caracteres.")
    if len(new_desc) > MAX_DESC:
        raise ValueError(f"Descrição excede {MAX_DESC} caracteres.")

    enc_name = encrypt(key, new_name)
    new_filename = _safe_name(task_id, enc_name)
    new_filepath = os.path.join(task_dir(), new_filename)
    with open(new_filepath, "w", encoding="utf-8") as f:
        f.write(encrypt(key, new_desc))
    if new_filename != entry["nome_arquivo"] and os.path.exists(filepath):
        os.remove(filepath)
    entry["nome_arquivo"] = new_filename
    if concluida is not None:
        entry["concluida"] = bool(concluida)
    save_index(tasks)


def delete_task(task_id: str) -> bool:
    tasks = load_index()
    entry = next((t for t in tasks if t["id"] == task_id), None)
    if entry is None:
        return False
    filepath = os.path.join(task_dir(), entry["nome_arquivo"])
    if os.path.exists(filepath):
        os.remove(filepath)
    tasks = [t for t in tasks if t["id"] != task_id]
    save_index(tasks)
    return True


# ---------- wrappers interativos (usados pela TUI) ----------

def _prompt_limited(label: str, max_len: int) -> str:
    while True:
        val = input(f"{label} (máx {max_len} chars): ")
        if len(val) <= max_len:
            return val
        print(f"⚠️ Excede {max_len} caracteres.")


def prompt_create(password: str):
    name = _prompt_limited("Nome da tarefa", MAX_NAME)
    desc = _prompt_limited("Descrição", MAX_DESC)
    create_task_values(password, name, desc)
    print("✅ Tarefa criada com sucesso!")


def prompt_list(password: str):
    try:
        tasks = list_tasks(password)
    except WrongPassword as e:
        print(f"⚠️ {e}")
        return
    if not tasks:
        print("ℹ️ Nenhuma tarefa encontrada.")
        return
    for t in tasks:
        flag = "✔" if t["concluida"] else "○"
        print(f"\nID: {t['id']}\n{flag} {t['nome']}\n   {t['desc']}\n"
              f"   criada em {t['data_criacao']}\n{'─' * 30}")


def prompt_edit(password: str):
    try:
        tasks = list_tasks(password)
    except WrongPassword as e:
        print(f"⚠️ {e}")
        return
    if not tasks:
        print("ℹ️ Nenhuma tarefa.")
        return
    for i, t in enumerate(tasks, 1):
        print(f"{i}. [{t['id'][:8]}] {t['nome']}")
    try:
        idx = int(input("Número da tarefa a editar: ")) - 1
        task_id = tasks[idx]["id"]
    except (ValueError, IndexError):
        print("❌ Índice inválido.")
        return
    new_name = input(f"Novo nome (vazio = manter '{tasks[idx]['nome']}'): ")
    new_desc = input("Nova descrição (vazio = manter): ")
    concluida = input("Concluída? (s/n/vazio = manter): ").strip().lower()
    try:
        edit_task_values(
            password, task_id,
            name=new_name or None,
            desc=new_desc or None,
            concluida={"s": True, "n": False}.get(concluida),
        )
        print("✅ Tarefa editada!")
    except (WrongPassword, ValueError) as e:
        print(f"❌ {e}")


def prompt_delete(password: str):
    try:
        tasks = list_tasks(password)
    except WrongPassword as e:
        print(f"⚠️ {e}")
        return
    if not tasks:
        print("ℹ️ Nenhuma tarefa.")
        return
    for i, t in enumerate(tasks, 1):
        print(f"{i}. [{t['id'][:8]}] {t['nome']}")
    try:
        idx = int(input("Número da tarefa a excluir: ")) - 1
        task_id = tasks[idx]["id"]
    except (ValueError, IndexError):
        print("❌ Índice inválido.")
        return
    if delete_task(task_id):
        print("✅ Tarefa excluída!")
    else:
        print("❌ Tarefa não encontrada.")
